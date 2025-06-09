"""
Company (Firma) related views.
"""

from .helpers import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Q, Case, When, Value, DecimalField
from django.db.models.functions import Coalesce
from ..models import Firmalar, Faturalar, Seferler, Ulkeler, Sehirler
import logging
from decimal import Decimal
import xlwt
from django.http import HttpResponse
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from sefer_app.utils import get_firma_unvan

logger = logging.getLogger(__name__)

def firma_list(request):
    """List all companies with filtering options."""
    # Base queryset
    firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    
    # Get filter parameters
    aktiflik = request.GET.get('aktiflik', 'all')
    ulke_id = request.GET.get('ulke', '')
    sehir_id = request.GET.get('sehir', '')
    arama = request.GET.get('arama', '')
    
    # Apply filters
    if aktiflik != 'all':
        aktif_mi = True if aktiflik == 'active' else False
        firmalar = firmalar.filter(AktifMi=aktif_mi)
        
    if ulke_id:
        firmalar = firmalar.filter(Ulke=ulke_id)
        
    if sehir_id:
        firmalar = firmalar.filter(Sehir=sehir_id)
    
    if arama:
        firmalar = firmalar.filter(
            Q(FirmaAdi__icontains=arama) | 
            Q(YetkiliKisi__icontains=arama) |
            Q(Eposta__icontains=arama) |
            Q(Telefon__icontains=arama) |
            Q(VergiNumarasi__icontains=arama)
        )
    
    # Check for export parameter
    export_format = request.GET.get('export', '')
    if export_format == 'pdf':
        return export_firma_pdf(request, firmalar)
    elif export_format == 'excel':
        return export_firma_excel(request, firmalar)
    
    # Count by status for statistics
    aktif_firma_sayisi = Firmalar.objects.filter(AktifMi=True).count()
    pasif_firma_sayisi = Firmalar.objects.filter(AktifMi=False).count()
    
    # Count by company type for statistics
    musteri_sayisi = Firmalar.objects.filter(FirmaTipi='Müşteri').count()
    tedarikci_sayisi = Firmalar.objects.filter(FirmaTipi='Tedarikçi').count()
    nakliyeci_sayisi = Firmalar.objects.filter(FirmaTipi='Nakliyeci').count()
    
    # Calculate financial statistics
    # Total receivables (Toplam Alacak) - Money owed to the company
    toplam_alacak = Faturalar.objects.filter(
        FaturaTipi__in=['Satış', 'Nakliye']
    ).aggregate(
        total=Coalesce(Sum(F('ToplamTutar') - F('OdenenTutar')), Decimal('0'), output_field=DecimalField())
    )['total']
    
    # Total debt (Toplam Borç) - Money the company owes to others
    toplam_borc = Faturalar.objects.filter(
        FaturaTipi='Alış'
    ).aggregate(
        total=Coalesce(Sum(F('ToplamTutar') - F('OdenenTutar')), Decimal('0'), output_field=DecimalField())
    )['total']
    
    # Calculate total balance as before for backward compatibility
    toplam_bakiye = toplam_alacak - toplam_borc
    
    # Get countries and cities for filter dropdowns
    ulkeler = Ulkeler.objects.all().order_by('ulke_adi')
    sehirler = Sehirler.objects.all().order_by('sehir_adi')
    
    context = {
        'firmalar': firmalar,
        'ulkeler': ulkeler,
        'sehirler': sehirler,
        'aktif_firma_sayisi': aktif_firma_sayisi,
        'pasif_firma_sayisi': pasif_firma_sayisi,
        'toplam_firma_sayisi': firmalar.count(),
        'musteri_sayisi': musteri_sayisi,
        'tedarikci_sayisi': tedarikci_sayisi,
        'nakliyeci_sayisi': nakliyeci_sayisi,
        'toplam_alacak': toplam_alacak,
        'toplam_borc': toplam_borc,
        'toplam_bakiye': toplam_bakiye,
        # Keep current filters for pagination
        'aktiflik_filtre': aktiflik,
        'ulke_filtre': ulke_id,
        'sehir_filtre': sehir_id,
        'arama_filtre': arama,
    }
    return render(request, 'sefer_app/firma_list.html', context)

def export_firma_pdf(request, firmalar_queryset=None):
    """Generate PDF report with company list."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Use provided queryset or get all companies
    if firmalar_queryset is None:
        firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    else:
        firmalar = firmalar_queryset
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="firma_listesi.pdf"'
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='TitleStyle', 
        parent=styles['Heading1'], 
        alignment=TA_CENTER,
        fontName=font_bold,
        fontSize=14
    )
    
    subtitle_style = ParagraphStyle(
        name='SubtitleStyle',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=12
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10
    )
    
    footer_style = ParagraphStyle(
        name='FooterStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        alignment=TA_CENTER
    )
    
    # Create content elements
    elements = []
    
    # Add title
    elements.append(Paragraph(get_firma_unvan(), title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(turkish_safe_text("CARİ LİSTESİ"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Create table data
    data = [
        [
            turkish_safe_text("Cari Adı"), 
            turkish_safe_text("Tip"),
            turkish_safe_text("Vergi No"), 
            turkish_safe_text("Yetkili"), 
            turkish_safe_text("Telefon"), 
            turkish_safe_text("Alacak"),
            turkish_safe_text("Borç"),
            turkish_safe_text("Bakiye"),
            turkish_safe_text("Durum")
        ]
    ]
    
    # Add company data rows
    for firma in firmalar:
        # Calculate financial data for this specific company
        if firma.FirmaTipi == 'Tedarikçi':
            # For suppliers: we track Alış (purchase) invoices
            borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
            tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
            alacak = 0
            borc = borc_toplam - tahsilat_toplam
        else:
            # For customers/carriers: we track Satış (sales) and Nakliye invoices
            borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
            tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
            alacak = borc_toplam - tahsilat_toplam
            borc = 0
        
        # Calculate balance
        bakiye = alacak - borc
        
        # Format status
        durum = turkish_safe_text("Aktif" if firma.AktifMi else "Pasif")
        
        # Add row to table data
        data.append([
            turkish_safe_text(get_first_two_words(firma.FirmaAdi)),
            turkish_safe_text(firma.FirmaTipi),
            turkish_safe_text(firma.VergiNumarasi or "-"),
            turkish_safe_text(get_first_two_words(firma.YetkiliKisi) if firma.YetkiliKisi else "-"),
            firma.Telefon or "-",
            format_currency(alacak),
            format_currency(borc),
            format_currency(bakiye),
            durum
        ])
    
    # Calculate column widths
    col_widths = [4*cm, 2*cm, 2.5*cm, 2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 1*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    
    # Apply table styles
    style = TableStyle([
        # Headers
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (5, 1), (7, -1), 'RIGHT'),  # Right align amounts
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Add footer with date and page number
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(turkish_safe_text(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), footer_style))
    elements.append(Paragraph(turkish_safe_text(f"© {datetime.now().year} NextSefer"), footer_style))
    
    # Build PDF
    doc.build(elements)
    return response

def export_firma_excel(request, firmalar_queryset=None):
    """Export company list as Excel."""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="firma_listesi.xls"'
    
    # Use provided queryset or get all companies
    if firmalar_queryset is None:
        firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    else:
        firmalar = firmalar_queryset
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Cari Listesi')
    
    # Sheet header
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Add title to Excel
    ws.write(row_num, 0, get_firma_unvan(), font_style)
    row_num += 1
    
    # Add report title
    ws.write(row_num, 0, "Cari Listesi", font_style)
    row_num += 1
    
    # Add report generation date
    ws.write(row_num, 0, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", font_style)
    row_num += 2  # Add an extra row for spacing
    
    # Column headers
    columns = ['Cari Adı', 'Tip', 'Vergi No', 'Yetkili', 'Telefon', 'E-posta', 'Adres', 'Alacak', 'Borç', 'Bakiye', 'Durum']
    
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    # Sheet body
    font_style = xlwt.XFStyle()
    
    for firma in firmalar:
        row_num += 1
        
        # Calculate financial data for this specific company
        if firma.FirmaTipi == 'Tedarikçi':
            # For suppliers: we track Alış (purchase) invoices
            borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
            tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
            alacak = 0
            borc = borc_toplam - tahsilat_toplam
        else:
            # For customers/carriers: we track Satış (sales) and Nakliye invoices
            borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
            tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
            alacak = borc_toplam - tahsilat_toplam
            borc = 0
        
        # Calculate balance
        bakiye = alacak - borc
        
        # Format status
        durum = "Aktif" if firma.AktifMi else "Pasif"
        
        # Add data to row
        col_num = 0
        ws.write(row_num, col_num, firma.FirmaAdi); col_num += 1
        ws.write(row_num, col_num, firma.FirmaTipi); col_num += 1
        ws.write(row_num, col_num, firma.VergiNumarasi or "-"); col_num += 1
        ws.write(row_num, col_num, firma.YetkiliKisi or "-"); col_num += 1
        ws.write(row_num, col_num, firma.Telefon or "-"); col_num += 1
        ws.write(row_num, col_num, firma.Eposta or "-"); col_num += 1
        ws.write(row_num, col_num, firma.Adres or "-"); col_num += 1
        ws.write(row_num, col_num, float(alacak)); col_num += 1
        ws.write(row_num, col_num, float(borc)); col_num += 1
        ws.write(row_num, col_num, float(bakiye)); col_num += 1
        ws.write(row_num, col_num, durum)
    
    wb.save(response)
    return response

def firma_detail(request, pk):
    """Display company details."""
    firma = get_object_or_404(Firmalar, pk=pk)
    
    # Get related objects
    seferler = Seferler.objects.filter(firma=firma).order_by('-cikis_tarihi')
    faturalar = Faturalar.objects.filter(Firma=firma).order_by('-FaturaTarihi')
    
    # Calculate statistics
    sefer_sayisi = seferler.count()
    aktif_sefer_sayisi = seferler.filter(durum='Aktif').count()
    
    # Get the date of the most recent transaction
    son_islem_tarihi = faturalar.order_by('-FaturaTarihi').values_list('FaturaTarihi', flat=True).first() if faturalar.exists() else None
    
    # Get country and city if available
    ulke = firma.Ulke if hasattr(firma, 'Ulke') else None
    sehir = firma.Sehir if hasattr(firma, 'Sehir') else None
    
    # Financial calculations - simplified approach
    if firma.FirmaTipi == 'Tedarikçi':
        # For suppliers: we track Alış (purchase) invoices
        borc_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
    else:
        # For customers/carriers: we track Satış (sales) and Nakliye invoices
        borc_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
    
    # Calculate balance
    bakiye = borc_toplam - tahsilat_toplam
    
    # Also calculate overall totals for reference
    alis_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    satis_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    
    print(f"DEBUG: Firma={firma.FirmaAdi}, Tip={firma.FirmaTipi}")
    print(f"DEBUG: Fatura Tipleri: {list(faturalar.values_list('FaturaTipi', flat=True))}")
    print(f"DEBUG: Borç={borc_toplam}, Tahsilat={tahsilat_toplam}, Bakiye={bakiye}")
    
    context = {
        'firma': firma,
        'seferler': seferler[:5],  # Limit to 5 recent trips
        'faturalar': faturalar[:5],  # Limit to 5 recent invoices
        'sefer_sayisi': sefer_sayisi,
        'aktif_sefer_sayisi': aktif_sefer_sayisi,
        'alis_toplam': alis_toplam,
        'satis_toplam': satis_toplam,
        'borc_toplam': borc_toplam,
        'tahsilat_toplam': tahsilat_toplam,
        'bakiye': bakiye,
        'odenmemis_tutar': borc_toplam - tahsilat_toplam,
        'son_islem_tarihi': son_islem_tarihi,
        'ulke': ulke,
        'sehir': sehir,
    }
    return render(request, 'sefer_app/firma_detail.html', context)


def firma_create(request):
    """Create a new company."""
    ulkeler = Ulkeler.objects.all().order_by('ulke_adi')
    sehirler = Sehirler.objects.all().order_by('sehir_adi')
    
    print("Firma create view çağrıldı")
    
    if request.method == 'POST':
        print("POST verileri:", request.POST)
        try:
            firma_adi = request.POST.get('firma_adi')
            if not firma_adi:
                messages.error(request, 'Firma adı zorunludur.')
                context = {'ulkeler': ulkeler, 'sehirler': sehirler}
                return render(request, 'sefer_app/firma_form.html', context)
            
            # Formdan gelen değerler
            firma_tipi = request.POST.get('firma_tipi', '')
            para_birimi = request.POST.get('para_birimi', 'EUR')
            
            print(f"Firma Adı: {firma_adi}")
            print(f"Firma Tipi: {firma_tipi}")
            print(f"Para Birimi: {para_birimi}")
            
            # Vergi numarası kontrolü - unique olduğu için kontrol edelim
            vergi_numarasi = request.POST.get('vergi_numarasi', '')
            if vergi_numarasi:
                # Eğer aynı vergi numarasına sahip başka firma varsa
                existing_firma = Firmalar.objects.filter(VergiNumarasi=vergi_numarasi).first()
                if existing_firma:
                    messages.error(request, f'Bu vergi numarası ile kayıtlı firma zaten mevcut: {existing_firma.FirmaAdi}')
                    context = {'ulkeler': ulkeler, 'sehirler': sehirler}
                    return render(request, 'sefer_app/firma_form.html', context)
            
            # VergiNumarasi alanı unique ama null olabilir
            # Boş string gönderildiğinde hata vermemesi için None atayalım
            if vergi_numarasi == '':
                vergi_numarasi = None
                
            # Model nesnesini oluştur
            firma = Firmalar(
                FirmaAdi=firma_adi,
                FirmaTipi=firma_tipi,
                YetkiliKisi=request.POST.get('yetkili_kisi', ''),
                Eposta=request.POST.get('eposta', ''),
                Telefon=request.POST.get('telefon', ''),
                Adres=request.POST.get('adres', ''),
                VergiDairesi=request.POST.get('vergi_dairesi', ''),
                VergiNumarasi=vergi_numarasi,
                WebSitesi=request.POST.get('web_sitesi', ''),
                AktifMi=request.POST.get('aktif_mi') == 'True',
                ParaBirimi=para_birimi,
                Notlar=request.POST.get('notlar', '')
            )
            
            # Assign country and city if provided
            ulke_id = request.POST.get('ulke')
            if ulke_id:
                # Use Ulke field instead of Ulke_id
                firma.Ulke = Ulkeler.objects.get(pk=ulke_id)
            
            sehir_id = request.POST.get('sehir')
            if sehir_id:
                # Use Sehir field instead of Sehir_id
                firma.Sehir = Sehirler.objects.get(pk=sehir_id)
                
            print("Firma kaydediliyor...")
            firma.save()
            print(f"Firma kaydedildi. ID: {firma.id}")
            
            messages.success(request, f"'{firma_adi}' başarıyla oluşturuldu.")
            return redirect('firma_detail', pk=firma.id)
            
        except Exception as e:
            import traceback
            print("HATA OLUŞTU:", str(e))
            print(traceback.format_exc())
            messages.error(request, f'Firma oluşturma hatası: {str(e)}')
    
    context = {
        'ulkeler': ulkeler,
        'sehirler': sehirler
    }
    return render(request, 'sefer_app/firma_form.html', context)


def firma_update(request, pk):
    """Update an existing company."""
    firma = get_object_or_404(Firmalar, pk=pk)
    ulkeler = Ulkeler.objects.all().order_by('ulke_adi')
    sehirler = Sehirler.objects.all().order_by('sehir_adi')
    
    print(f"Firma update view çağrıldı, ID: {pk}")
    
    if request.method == 'POST':
        print("POST verileri:", request.POST)
        try:
            firma_adi = request.POST.get('firma_adi')
            if not firma_adi:
                messages.error(request, 'Firma adı zorunludur.')
                context = {
                    'firma': firma,
                    'ulkeler': ulkeler,
                    'sehirler': sehirler
                }
                return render(request, 'sefer_app/firma_form.html', context)
            
            # Formdan gelen değerler
            firma_tipi = request.POST.get('firma_tipi', '')
            para_birimi = request.POST.get('para_birimi', 'EUR')
            
            # Vergi numarası kontrolü - sadece değiştiyse kontrol et
            vergi_numarasi = request.POST.get('vergi_numarasi', '')
            if vergi_numarasi and vergi_numarasi != firma.VergiNumarasi:
                # Eğer aynı vergi numarasına sahip başka firma varsa
                existing_firma = Firmalar.objects.filter(VergiNumarasi=vergi_numarasi).exclude(pk=firma.pk).first()
                if existing_firma:
                    messages.error(request, f'Bu vergi numarası ile kayıtlı başka bir firma zaten mevcut: {existing_firma.FirmaAdi}')
                    context = {'firma': firma, 'ulkeler': ulkeler, 'sehirler': sehirler}
                    return render(request, 'sefer_app/firma_form.html', context)
            
            # VergiNumarasi alanı unique ama null olabilir
            # Boş string gönderildiğinde hata vermemesi için None atayalım
            if vergi_numarasi == '':
                vergi_numarasi = None
                
            firma.FirmaAdi = firma_adi
            firma.FirmaTipi = firma_tipi
            firma.YetkiliKisi = request.POST.get('yetkili_kisi', '')
            firma.Eposta = request.POST.get('eposta', '')
            firma.Telefon = request.POST.get('telefon', '')
            firma.Adres = request.POST.get('adres', '')
            firma.VergiDairesi = request.POST.get('vergi_dairesi', '')
            firma.VergiNumarasi = vergi_numarasi
            firma.WebSitesi = request.POST.get('web_sitesi', '')
            firma.AktifMi = request.POST.get('aktif_mi') == 'True'
            firma.ParaBirimi = para_birimi
            firma.Notlar = request.POST.get('notlar', '')
            
            # Update country and city
            ulke_id = request.POST.get('ulke')
            if ulke_id:
                # Use Ulke field instead of Ulke_id
                firma.Ulke = Ulkeler.objects.get(pk=ulke_id)
            else:
                firma.Ulke = None
            
            sehir_id = request.POST.get('sehir')
            if sehir_id:
                # Use Sehir field instead of Sehir_id
                firma.Sehir = Sehirler.objects.get(pk=sehir_id)
            else:
                firma.Sehir = None
                
            print("Firma güncelleniyor...")
            firma.save()
            print(f"Firma güncellendi. ID: {firma.id}")
            
            messages.success(request, f"'{firma_adi}' başarıyla güncellendi.")
            return redirect('firma_detail', pk=firma.id)
            
        except Exception as e:
            import traceback
            print("HATA OLUŞTU:", str(e))
            print(traceback.format_exc())
            messages.error(request, f'Firma güncelleme hatası: {str(e)}')
    
    context = {
        'firma': firma,
        'ulkeler': ulkeler,
        'sehirler': sehirler
    }
    return render(request, 'sefer_app/firma_form.html', context)


def firma_delete(request, pk):
    """Delete a company."""
    firma = get_object_or_404(Firmalar, pk=pk)
    
    if request.method == 'POST':
        try:
            # Check if there are related objects
            sefer_count = Seferler.objects.filter(firma=firma).count()
            fatura_count = Faturalar.objects.filter(Firma=firma).count()
            
            if sefer_count > 0 or fatura_count > 0:
                messages.error(
                    request, 
                    f"Bu firmaya bağlı {sefer_count} sefer ve {fatura_count} fatura bulunduğu için silinemez!"
                )
                return redirect('firma_detail', pk=pk)
            
            firma_adi = firma.FirmaAdi
            firma.delete()
            messages.success(request, f"'{firma_adi}' başarıyla silindi.")
            return redirect('firma_list')
            
        except Exception as e:
            messages.error(request, f'Firma silme hatası: {str(e)}')
            return redirect('firma_detail', pk=pk)
    
    context = {
        'firma': firma,
    }
    return render(request, 'sefer_app/firma_confirm_delete.html', context)


def get_cities_by_country(request):
    """AJAX view to get cities based on country."""
    ulke_id = request.GET.get('ulke_id', None)
    if ulke_id:
        sehirler = Sehirler.objects.filter(ulke_id=ulke_id).order_by('sehir_adi').values('id', 'sehir_adi')
        return JsonResponse(list(sehirler), safe=False)
    return JsonResponse([], safe=False)


def firma_print(request, pk):
    """Print company details."""
    firma = get_object_or_404(Firmalar, pk=pk)
    
    # Get related objects
    seferler = Seferler.objects.filter(firma=firma).order_by('-cikis_tarihi')
    faturalar = Faturalar.objects.filter(Firma=firma).order_by('-FaturaTarihi')
    
    # Calculate statistics
    sefer_sayisi = seferler.count()
    aktif_sefer_sayisi = seferler.filter(durum='Aktif').count()
    
    # Get the date of the most recent transaction
    son_islem_tarihi = faturalar.order_by('-FaturaTarihi').values_list('FaturaTarihi', flat=True).first() if faturalar.exists() else None
    
    # Get country and city if available
    ulke = firma.Ulke if hasattr(firma, 'Ulke') else None
    sehir = firma.Sehir if hasattr(firma, 'Sehir') else None
    
    # Financial calculations
    if firma.FirmaTipi == 'Tedarikçi':
        # For suppliers: we track Alış (purchase) invoices
        borc_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
    else:
        # For customers/carriers: we track Satış (sales) and Nakliye invoices
        borc_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
    
    # Calculate balance
    bakiye = borc_toplam - tahsilat_toplam
    
    # Also calculate overall totals for reference
    alis_toplam = faturalar.filter(FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    satis_toplam = faturalar.filter(FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    
    print(f"DEBUG: Firma={firma.FirmaAdi}, Tip={firma.FirmaTipi}")
    print(f"DEBUG: Borç={borc_toplam}, Tahsilat={tahsilat_toplam}, Bakiye={bakiye}")
    
    context = {
        'firma': firma,
        'seferler': seferler,
        'faturalar': faturalar,
        'sefer_sayisi': sefer_sayisi,
        'aktif_sefer_sayisi': aktif_sefer_sayisi,
        'alis_toplam': alis_toplam,
        'satis_toplam': satis_toplam,
        'borc_toplam': borc_toplam,
        'tahsilat_toplam': tahsilat_toplam,
        'bakiye': bakiye,
        'odenmemis_tutar': borc_toplam - tahsilat_toplam,
        'son_islem_tarihi': son_islem_tarihi,
        'ulke': ulke,
        'sehir': sehir,
    }
    return render(request, 'sefer_app/firma_print.html', context)

def firma_pdf(request, pk):
    """Generate PDF report with company details."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    firma = get_object_or_404(Firmalar, pk=pk)
    
    # Get all seferler for counts
    tum_seferler = Seferler.objects.filter(firma=firma)
    
    # Calculate statistics
    sefer_sayisi = tum_seferler.count()
    aktif_sefer_sayisi = tum_seferler.filter(durum='Aktif').count()
    
    # Get related objects with limit
    seferler = Seferler.objects.filter(firma=firma).order_by('-cikis_tarihi')[:10]  # Limit to recent 10
    faturalar = Faturalar.objects.filter(Firma=firma).order_by('-FaturaTarihi')[:10]  # Limit to recent 10
    
    # Financial calculations
    if firma.FirmaTipi == 'Tedarikçi':
        # For suppliers: we track Alış (purchase) invoices
        borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
        alacak = 0
        borc = borc_toplam - tahsilat_toplam
    else:
        # For customers/carriers: we track Satış (sales) and Nakliye invoices
        borc_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
        tahsilat_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('OdenenTutar'))['OdenenTutar__sum'] or 0
        alacak = borc_toplam - tahsilat_toplam
        borc = 0
    
    # Calculate balance
    bakiye = alacak - borc
    
    # Also calculate overall totals for reference
    alis_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi='Alış').aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    satis_toplam = Faturalar.objects.filter(Firma=firma, FaturaTipi__in=['Satış', 'Nakliye']).aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="firma_{pk}_detay.pdf"'
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='TitleStyle', 
        parent=styles['Heading1'], 
        alignment=TA_CENTER,
        fontName=font_bold,
        fontSize=14
    )
    
    subtitle_style = ParagraphStyle(
        name='SubtitleStyle',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=12
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10
    )
    
    small_style = ParagraphStyle(
        name='SmallStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8
    )
    
    # Create content elements
    elements = []
    
    # Add title
    elements.append(Paragraph(get_firma_unvan(), title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(turkish_safe_text(f"CARİ DETAY: {get_first_two_words(firma.FirmaAdi)}"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Company general information
    elements.append(Paragraph(turkish_safe_text("Genel Bilgiler"), subtitle_style))
    
    # Company info table
    genel_data = [
        [turkish_safe_text("Cari Adı:"), turkish_safe_text(get_first_two_words(firma.FirmaAdi))],
        [turkish_safe_text("Cari Tipi:"), turkish_safe_text(firma.FirmaTipi)],
        [turkish_safe_text("Yetkili:"), turkish_safe_text(get_first_two_words(firma.YetkiliKisi) if firma.YetkiliKisi else "-")],
        [turkish_safe_text("Vergi No:"), turkish_safe_text(firma.VergiNumarasi or "-")],
        [turkish_safe_text("Telefon:"), firma.Telefon or "-"],
        [turkish_safe_text("E-posta:"), firma.Eposta or "-"],
        [turkish_safe_text("Adres:"), turkish_safe_text(firma.Adres or "-")],
        [turkish_safe_text("Durum:"), turkish_safe_text("Aktif" if firma.AktifMi else "Pasif")],
    ]
    
    table = Table(genel_data, colWidths=[3*cm, 15*cm])
    style = TableStyle([
        ('FONTNAME', (0, 0), (0, -1), font_bold),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ])
    table.setStyle(style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Financial information
    elements.append(Paragraph(turkish_safe_text("Mali Bilgiler"), subtitle_style))
    
    # Financial info table
    mali_data = [
        [turkish_safe_text("Alacak:"), format_currency(alacak)],
        [turkish_safe_text("Borç:"), format_currency(borc)],
        [turkish_safe_text("Bakiye:"), format_currency(bakiye)],
    ]
    
    table = Table(mali_data, colWidths=[3*cm, 15*cm])
    style = TableStyle([
        ('FONTNAME', (0, 0), (0, -1), font_bold),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ])
    table.setStyle(style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Recent invoices
    if faturalar.exists():
        elements.append(Paragraph(turkish_safe_text("Son Faturalar"), subtitle_style))
        fatura_data = [
            [
                turkish_safe_text("Fatura No"),
                turkish_safe_text("Tip"),
                turkish_safe_text("Tarih"),
                turkish_safe_text("Tutar"),
                turkish_safe_text("Ödenen"),
                turkish_safe_text("Durum")
            ]
        ]
        
        for fatura in faturalar:
            fatura_data.append([
                fatura.FaturaNo,
                turkish_safe_text(fatura.FaturaTipi),
                fatura.FaturaTarihi.strftime('%d.%m.%Y') if fatura.FaturaTarihi else "-",
                format_currency(fatura.ToplamTutar),
                format_currency(fatura.OdenenTutar),
                turkish_safe_text(fatura.OdemeDurumu)
            ])
        
        table = Table(fatura_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3*cm, 3*cm, 4*cm], repeatRows=1)
        style = TableStyle([
            # Headers
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            
            # Body
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),  # Right align amounts
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ])
        table.setStyle(style)
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
    
    # Recent trips
    if seferler.exists():
        elements.append(Paragraph(turkish_safe_text("Son Seferler"), subtitle_style))
        sefer_data = [
            [
                turkish_safe_text("Sefer Kodu"),
                turkish_safe_text("Rota"),
                turkish_safe_text("Çıkış Tarihi"),
                turkish_safe_text("Durum")
            ]
        ]
        
        for sefer in seferler:
            rota = f"{sefer.baslangic_sehri.sehir_adi if sefer.baslangic_sehri else '-'} → {sefer.bitis_sehri.sehir_adi if sefer.bitis_sehri else '-'}"
            sefer_data.append([
                sefer.sefer_kodu,
                turkish_safe_text(rota),
                sefer.cikis_tarihi.strftime('%d.%m.%Y') if sefer.cikis_tarihi else "-",
                turkish_safe_text(sefer.durum)
            ])
        
        table = Table(sefer_data, colWidths=[3*cm, 9*cm, 3*cm, 3*cm], repeatRows=1)
        style = TableStyle([
            # Headers
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            
            # Body
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ])
        table.setStyle(style)
        elements.append(table)
    
    # Add footer with date and page number
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(turkish_safe_text(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), small_style))
    elements.append(Paragraph(turkish_safe_text(f"© {datetime.now().year} NextSefer"), small_style))
    
    # Build PDF
    doc.build(elements)
    return response 