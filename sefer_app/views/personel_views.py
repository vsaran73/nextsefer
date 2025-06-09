"""
Personnel (Personel) related views.
"""

from .helpers import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import datetime
import xlwt
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from ..models import Personeller, Seferler, PersonelOdeme, Kasalar, GenelKasaHareketi
from sefer_app.utils import get_firma_unvan

def generate_personel_odeme_no():
    """Generate a document number in the format PER-MMYY-X"""
    today = datetime.now()
    month_year = f"{today.month:02d}{str(today.year)[-2:]}"  # MMYY format
    prefix = f"PER-{month_year}-"
    
    # Check for existing document numbers and increment
    try:
        latest_odeme = PersonelOdeme.objects.filter(belge_no__startswith=prefix).order_by('-belge_no').first()
        if latest_odeme and latest_odeme.belge_no:
            # Extract the number part and increment
            last_num = int(latest_odeme.belge_no.split('-')[-1])
            return f"{prefix}{last_num + 1:04d}"
    except Exception as e:
        print(f"Personel ödeme belge numarası oluşturulurken hata: {e}")
    
    # If no existing number or error, start with 1
    return f"{prefix}0001"

def personel_list(request):
    """List all personnel."""
    personeller = Personeller.objects.all().order_by('PerAd')
    
    # Get filter parameters
    arama = request.GET.get('arama', '')
    durum = request.GET.get('durum', '')
    departman = request.GET.get('departman', '')
    pozisyon = request.GET.get('pozisyon', '')
    ise_baslangic = request.GET.get('ise_baslangic', '')
    surucu_tipi = request.GET.get('surucu_tipi', '')
    
    # Apply filters
    if arama:
        personeller = personeller.filter(
            Q(PerAd__icontains=arama) | 
            Q(PerSoyad__icontains=arama) |
            Q(Telefon__icontains=arama) |
            Q(VatandaslikNo__icontains=arama)
        )
    
    if durum:
        personeller = personeller.filter(Durum=durum)
    
    if departman:
        personeller = personeller.filter(Departman=departman)
    
    if pozisyon:
        personeller = personeller.filter(Pozisyon=pozisyon)
    
    if ise_baslangic:
        personeller = personeller.filter(IseBaslangicTarihi=ise_baslangic)
    
    if surucu_tipi == 'Evet':
        # Sürücü pozisyonları (örneğin: "Şoför", "Tır Şoförü", "Servis Şoförü" gibi pozisyonlar)
        personeller = personeller.filter(
            Q(Pozisyon__icontains='şoför') | 
            Q(Pozisyon__icontains='sofor') |
            Q(Pozisyon__icontains='şofôr') | 
            Q(Pozisyon__icontains='şöfor') |
            Q(Pozisyon__icontains='soför') |
            Q(Pozisyon__icontains='driver') |
            Q(Pozisyon__icontains='sürücü') |
            Q(Pozisyon__icontains='surucu') |
            Q(Departman__icontains='şoför') |
            Q(Departman__icontains='sofor') |
            Q(Departman__icontains='sürücü')
        )
    elif surucu_tipi == 'Hayır':
        # Sürücü olmayan pozisyonlar
        personeller = personeller.exclude(
            Q(Pozisyon__icontains='şoför') | 
            Q(Pozisyon__icontains='sofor') |
            Q(Pozisyon__icontains='şofôr') | 
            Q(Pozisyon__icontains='şöfor') |
            Q(Pozisyon__icontains='soför') |
            Q(Pozisyon__icontains='driver') |
            Q(Pozisyon__icontains='sürücü') |
            Q(Pozisyon__icontains='surucu') |
            Q(Departman__icontains='şoför') |
            Q(Departman__icontains='sofor') |
            Q(Departman__icontains='sürücü')
        )
    
    # Check for export parameter
    export_format = request.GET.get('export', '')
    if export_format == 'pdf':
        return export_personel_pdf(request, personeller)
    elif export_format == 'excel':
        return export_personel_excel(request, personeller)
    
    # Count by status for statistics
    aktif_personel_sayisi = Personeller.objects.filter(Durum='Aktif').count()
    izinli_personel_sayisi = Personeller.objects.filter(Durum='İzinli').count()
    
    # Get distinct pozisyon list for filter dropdown
    pozisyonlar = Personeller.objects.exclude(Pozisyon='').values_list('Pozisyon', flat=True).distinct()
    departmanlar = Personeller.objects.exclude(Departman='').values_list('Departman', flat=True).distinct()
    
    # Count different pozisyon types for the band statistics
    yonetici_sayisi = Personeller.objects.filter(
        Q(Pozisyon__icontains='müdür') | 
        Q(Pozisyon__icontains='yönetici') |
        Q(Pozisyon__icontains='direktör') |
        Q(Pozisyon__icontains='ceo') |
        Q(Pozisyon__icontains='cfo')
    ).count()
    
    # Count personnel with active status
    active_driver_query = Q(Durum='Aktif') & (
        Q(Pozisyon__exact='Şoför') |  # Exact match
        Q(Pozisyon__exact='Sofor') |  # Exact match without Turkish characters
        Q(Pozisyon__iexact='şoför') |  # Case insensitive exact
        Q(Pozisyon__iexact='sofor') |  # Case insensitive exact without Turkish characters
        Q(Pozisyon__icontains='şoför') | 
        Q(Pozisyon__icontains='sofor') |
        Q(Pozisyon__icontains='şofôr') | 
        Q(Pozisyon__icontains='şöfor') |
        Q(Pozisyon__icontains='soför') |
        Q(Pozisyon__icontains='driver') |
        Q(Pozisyon__icontains='sürücü') |
        Q(Pozisyon__icontains='surucu') |
        Q(Departman__icontains='şoför') |
        Q(Departman__icontains='sofor') |
        Q(Departman__icontains='sürücü')
    )
    
    # Debug print - print all personnel positions for inspection
    print("--- DEBUG: All personnel positions ---")
    for p in Personeller.objects.all():
        print(f"ID: {p.id}, Name: {p.PerAd} {p.PerSoyad}, Position: '{p.Pozisyon}', Department: '{p.Departman}', Status: {p.Durum}")
    print("------------------------------------")
    
    surucu_sayisi = Personeller.objects.filter(active_driver_query).count()
    
    # Count personnel with non-driver positions (for "diğer pozisyonlar")
    ofis_personeli_sayisi = Personeller.objects.filter(Durum='Aktif').exclude(active_driver_query).count()
    
    # Calculate average salary from non-zero values
    ortalama_maas = Personeller.objects.filter(
        Q(Maas__gt=0) & 
        Q(Durum__in=['Aktif', 'İzinli'])
    ).aggregate(Avg('Maas'))['Maas__avg'] or 0
    
    context = {
        'personeller': personeller,
        'aktif_personel_sayisi': aktif_personel_sayisi,
        'izinli_personel_sayisi': izinli_personel_sayisi,
        'toplam_personel_sayisi': Personeller.objects.count(),
        'surucu_sayisi': surucu_sayisi,
        'yonetici_sayisi': yonetici_sayisi,
        'ofis_personeli_sayisi': ofis_personeli_sayisi,
        'ortalama_maas': ortalama_maas,
        'pozisyonlar': pozisyonlar,
        'departmanlar': departmanlar,
        
        # Filters for template
        'arama_filtre': arama,
        'durum_filtre': durum,
        'departman_filtre': departman,
        'pozisyon_filtre': pozisyon,
        'ise_baslangic_filtre': ise_baslangic,
        'surucu_tipi_filtre': surucu_tipi,
    }
    return render(request, 'sefer_app/personel_list.html', context)

def export_personel_pdf(request, personeller_queryset=None):
    """Generate PDF report with personnel list."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Use provided queryset or get all personnel
    if personeller_queryset is None:
        personeller = Personeller.objects.all().order_by('PerAd')
    else:
        personeller = personeller_queryset
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="personel_listesi.pdf"'
    
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
    elements.append(Paragraph(turkish_safe_text("PERSONEL LİSTESİ"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Create table data
    data = [
        [
            turkish_safe_text("Adı Soyadı"),
            turkish_safe_text("Pozisyon"),
            turkish_safe_text("Departman"),
            turkish_safe_text("Telefon"),
            turkish_safe_text("İşe Başlama"),
            turkish_safe_text("Maaş"),
            turkish_safe_text("Durum")
        ]
    ]
    
    # Add personnel data rows
    for personel in personeller:
        # Format dates
        ise_baslama = personel.IseBaslangicTarihi.strftime('%d.%m.%Y') if personel.IseBaslangicTarihi else "-"
        
        # Format status
        durum = turkish_safe_text(personel.Durum)
        
        # Format full name
        tam_ad = f"{personel.PerAd} {personel.PerSoyad}"
        
        # Add row to table data
        data.append([
            turkish_safe_text(tam_ad),
            turkish_safe_text(personel.Pozisyon or "-"),
            turkish_safe_text(personel.Departman or "-"),
            personel.Telefon or "-",
            ise_baslama,
            format_currency(personel.Maas) if personel.Maas else "-",
            durum
        ])
    
    # Calculate column widths
    col_widths = [5*cm, 3*cm, 3*cm, 2.5*cm, 2.5*cm, 2*cm, 2*cm]
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
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),  # Right align amounts
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

def export_personel_excel(request, personeller_queryset=None):
    """Export personnel list as Excel."""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="personel_listesi.xls"'
    
    # Use provided queryset or get all personnel
    if personeller_queryset is None:
        personeller = Personeller.objects.all().order_by('PerAd')
    else:
        personeller = personeller_queryset
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Personel Listesi')
    
    # Sheet header
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Add title to Excel
    ws.write(row_num, 0, get_firma_unvan(), font_style)
    row_num += 1
    
    # Add report title
    ws.write(row_num, 0, "Personel Listesi", font_style)
    row_num += 1
    
    # Add report generation date
    ws.write(row_num, 0, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", font_style)
    row_num += 2  # Add an extra row for spacing
    
    # Column headers
    columns = ['Adı', 'Soyadı', 'Pozisyon', 'Departman', 'Telefon', 'E-posta', 'TC / Vat. No', 'İşe Başlama', 'İşten Ayrılma', 'Maaş', 'Durum']
    
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    # Sheet body
    font_style = xlwt.XFStyle()
    
    for personel in personeller:
        row_num += 1
        
        # Format dates
        ise_baslama = personel.IseBaslangicTarihi.strftime('%d.%m.%Y') if personel.IseBaslangicTarihi else "-"
        isten_ayrilma = "-"  # Default value
        
        # Safely check if IstenCikisTarihi attribute exists before accessing it
        if hasattr(personel, 'IstenCikisTarihi') and personel.IstenCikisTarihi:
            isten_ayrilma = personel.IstenCikisTarihi.strftime('%d.%m.%Y')
        
        # Add data to row
        col_num = 0
        ws.write(row_num, col_num, personel.PerAd); col_num += 1
        ws.write(row_num, col_num, personel.PerSoyad); col_num += 1
        ws.write(row_num, col_num, personel.Pozisyon or "-"); col_num += 1
        ws.write(row_num, col_num, personel.Departman or "-"); col_num += 1
        ws.write(row_num, col_num, personel.Telefon or "-"); col_num += 1
        ws.write(row_num, col_num, personel.Eposta or "-"); col_num += 1
        ws.write(row_num, col_num, personel.VatandaslikNo or "-"); col_num += 1
        ws.write(row_num, col_num, ise_baslama); col_num += 1
        ws.write(row_num, col_num, isten_ayrilma); col_num += 1
        ws.write(row_num, col_num, float(personel.Maas) if personel.Maas else 0); col_num += 1
        ws.write(row_num, col_num, personel.Durum)
    
    wb.save(response)
    return response

def personel_detail_pdf(request, pk):
    """Generate PDF report with personnel details."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    personel = get_object_or_404(Personeller, pk=pk)
    
    # Get related objects
    seferler = Seferler.objects.filter(personel=personel).order_by('-cikis_tarihi')[:10]  # Limit to recent 10
    odemeler = PersonelOdeme.objects.filter(personel=personel).order_by('-tarih')[:10]  # Limit to recent 10
    
    # Calculate total payments
    toplam_odeme = odemeler.aggregate(Sum('tutar'))['tutar__sum'] or 0
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="personel_{pk}_detay.pdf"'
    
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
    elements.append(Paragraph(turkish_safe_text(f"PERSONEL DETAY: {get_first_two_words(personel.PerAd + ' ' + personel.PerSoyad)}"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Personnel general information
    elements.append(Paragraph(turkish_safe_text("Genel Bilgiler"), subtitle_style))
    
    # Personnel info table
    genel_data = [
        [turkish_safe_text("Adı Soyadı:"), turkish_safe_text(get_first_two_words(f"{personel.PerAd} {personel.PerSoyad}"))],
        [turkish_safe_text("Pozisyon:"), turkish_safe_text(personel.Pozisyon or "-")],
        [turkish_safe_text("Departman:"), turkish_safe_text(personel.Departman or "-")],
        [turkish_safe_text("TC / Vat. No:"), turkish_safe_text(personel.VatandaslikNo or "-")],
        [turkish_safe_text("Telefon:"), personel.Telefon or "-"],
        [turkish_safe_text("E-posta:"), personel.Eposta or "-"],
        [turkish_safe_text("İşe Başlama:"), personel.IseBaslangicTarihi.strftime('%d.%m.%Y') if personel.IseBaslangicTarihi else "-"],
        [turkish_safe_text("İşten Ayrılma:"), "-"],
        [turkish_safe_text("Maaş:"), format_currency(personel.Maas) if personel.Maas else "-"],
        [turkish_safe_text("Durum:"), turkish_safe_text(personel.Durum)],
        [turkish_safe_text("Notlar:"), turkish_safe_text(personel.Aciklama or "-")],
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
    
    # Recent payments
    if odemeler.exists():
        elements.append(Paragraph(turkish_safe_text("Son Ödemeler"), subtitle_style))
        odeme_data = [
            [
                turkish_safe_text("Belge No"),
                turkish_safe_text("Tarih"),
                turkish_safe_text("Tutar"),
                turkish_safe_text("Açıklama")
            ]
        ]
        
        for odeme in odemeler:
            odeme_data.append([
                odeme.belge_no or "-",
                odeme.tarih.strftime('%d.%m.%Y') if odeme.tarih else "-",
                format_currency(odeme.tutar) if odeme.tutar else "-",
                turkish_safe_text(odeme.aciklama or "-")
            ])
        
        table = Table(odeme_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 9*cm], repeatRows=1)
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
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Right align amounts
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

def personel_detail(request, pk):
    """Display detailed information about a specific personnel."""
    personel = get_object_or_404(Personeller, pk=pk)
    
    # Get related trips
    seferler = Seferler.objects.filter(personel=personel).order_by('-cikis_tarihi')
    
    # Get payments
    odemeler = PersonelOdeme.objects.filter(personel=personel).order_by('-tarih')
    
    # Calculate total payments
    toplam_odeme = odemeler.aggregate(Sum('tutar'))['tutar__sum'] or 0
    
    # Get cash registers for payment form
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    # Generate default payment document number
    default_belge_no = generate_personel_odeme_no()
    
    # Get today's date for default value in payment form
    today = timezone.now()
    
    context = {
        'personel': personel,
        'seferler': seferler,
        'odemeler': odemeler,
        'toplam_odeme': toplam_odeme,
        'default_belge_no': default_belge_no,
        'today': today,
        'kasalar': kasalar,
    }
    return render(request, 'sefer_app/personel_detail.html', context)


def personel_create(request):
    """Create a new personnel."""
    if request.method == 'POST':
        try:
            per_ad = request.POST.get('per_ad', '')
            per_soyad = request.POST.get('per_soyad', '')
            
            if not per_ad or not per_soyad:
                messages.error(request, 'Ad ve soyad zorunludur.')
                return render(request, 'sefer_app/personel_form.html')
            
            personel = Personeller(
                PerAd=per_ad,
                PerSoyad=per_soyad,
                Telefon=request.POST.get('telefon', ''),
                Eposta=request.POST.get('eposta', ''),
                DogumTarihi=request.POST.get('dogum_tarihi') or None,
                VatandaslikNo=request.POST.get('vatandaslik_no', ''),
                Adres=request.POST.get('adres', ''),
                Departman=request.POST.get('departman', ''),
                Pozisyon=request.POST.get('pozisyon', ''),
                Maas=safe_decimal(request.POST.get('maas', '0')),
                IseBaslangicTarihi=request.POST.get('ise_baslangic_tarihi') or None,
                Durum=request.POST.get('durum', 'Aktif'),
                Aciklama=request.POST.get('aciklama', '')
            )
            personel.save()
            
            messages.success(request, f"{per_ad} {per_soyad} personeli başarıyla oluşturuldu.")
            return redirect('personel_detail', pk=personel.id)
            
        except Exception as e:
            messages.error(request, f'Personel oluşturma hatası: {str(e)}')
    
    return render(request, 'sefer_app/personel_form.html')


def personel_update(request, pk):
    """Update an existing personnel."""
    personel = get_object_or_404(Personeller, pk=pk)
    
    if request.method == 'POST':
        try:
            per_ad = request.POST.get('per_ad', '')
            per_soyad = request.POST.get('per_soyad', '')
            
            if not per_ad or not per_soyad:
                messages.error(request, 'Ad ve soyad zorunludur.')
                return render(request, 'sefer_app/personel_form.html', {'personel': personel})
            
            personel.PerAd = per_ad
            personel.PerSoyad = per_soyad
            personel.Telefon = request.POST.get('telefon', '')
            personel.Eposta = request.POST.get('eposta', '')
            personel.DogumTarihi = request.POST.get('dogum_tarihi') or None
            personel.VatandaslikNo = request.POST.get('vatandaslik_no', '')
            personel.Adres = request.POST.get('adres', '')
            personel.Departman = request.POST.get('departman', '')
            personel.Pozisyon = request.POST.get('pozisyon', '')
            personel.Maas = safe_decimal(request.POST.get('maas', '0'))
            personel.IseBaslangicTarihi = request.POST.get('ise_baslangic_tarihi') or None
            personel.Durum = request.POST.get('durum', 'Aktif')
            personel.Aciklama = request.POST.get('aciklama', '')
            
            personel.save()
            
            messages.success(request, f"{per_ad} {per_soyad} personeli başarıyla güncellendi.")
            return redirect('personel_detail', pk=personel.id)
            
        except Exception as e:
            messages.error(request, f'Personel güncelleme hatası: {str(e)}')
    
    context = {'personel': personel}
    return render(request, 'sefer_app/personel_form.html', context)


def personel_delete(request, pk):
    """Delete a personnel."""
    personel = get_object_or_404(Personeller, pk=pk)
    
    if request.method == 'POST':
        try:
            # Check if there are related trips
            sefer_count = Seferler.objects.filter(personel=personel).count()
            
            if sefer_count > 0:
                messages.error(
                    request,
                    f"Bu personele bağlı {sefer_count} sefer kaydı olduğu için silinemez."
                )
                return redirect('personel_detail', pk=pk)
            
            ad_soyad = f"{personel.PerAd} {personel.PerSoyad}"
            personel.delete()
            messages.success(request, f"{ad_soyad} personeli başarıyla silindi.")
            return redirect('personel_list')
            
        except Exception as e:
            messages.error(request, f'Personel silme hatası: {str(e)}')
            return redirect('personel_detail', pk=pk)
    
    context = {'personel': personel}
    return render(request, 'sefer_app/personel_confirm_delete.html', context)

def personel_odeme_create(request, personel_pk):
    """Create a new payment for a personnel."""
    personel = get_object_or_404(Personeller, pk=personel_pk)
    
    if request.method == 'POST':
        try:
            odeme_turu = request.POST.get('odeme_turu')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            tarih = request.POST.get('tarih')
            aciklama = request.POST.get('aciklama', '')
            belge_no = request.POST.get('belge_no', '')
            kasa_id = request.POST.get('kasa')
            
            # Basic validation
            if not odeme_turu or tutar <= 0 or not kasa_id:
                messages.error(request, 'Ödeme türü, tutar ve kasa zorunludur. Tutar pozitif olmalıdır.')
                return redirect('personel_detail', pk=personel_pk)
            
            if not tarih:
                tarih = timezone.now().date()
            
            # Generate document number if not provided
            if not belge_no:
                belge_no = generate_personel_odeme_no()
            
            # Get cash register
            kasa = Kasalar.objects.get(id=kasa_id)
                
            # Create payment
            odeme = PersonelOdeme(
                personel=personel,
                odeme_turu=odeme_turu,
                tutar=tutar,
                tarih=tarih,
                aciklama=aciklama,
                belge_no=belge_no,
                kasa=kasa
            )
            odeme.save()
            
            # Create cash register transaction
            personel_link = f"/personel/{personel.id}/"
            aciklama_text = f"{personel.PerAd} {personel.PerSoyad}"
            if aciklama:
                aciklama_text += f" - {aciklama}"
                
            hareket = GenelKasaHareketi.objects.create(
                kasa=kasa,
                hareket_tipi='Gider',
                kategori='Personel Ödemesi',
                gider_turu=odeme_turu,
                tutar=tutar,
                tarih=tarih,
                belge_no=belge_no,
                aciklama=aciklama_text
            )
            
            messages.success(
                request, 
                f"{personel.PerAd} {personel.PerSoyad} personeli için {odeme.odeme_turu} ödemesi başarıyla oluşturuldu."
            )
            
        except Exception as e:
            messages.error(request, f'Ödeme oluşturma hatası: {str(e)}')
    
    return redirect('personel_detail', pk=personel_pk)

def personel_odeme_update(request, pk):
    """Update an existing payment."""
    odeme = get_object_or_404(PersonelOdeme, pk=pk)
    personel_pk = odeme.personel.pk
    
    if request.method == 'POST':
        try:
            # Store old values for updating cash register transaction
            old_kasa_id = odeme.kasa.id if odeme.kasa else None
            old_tutar = odeme.tutar
            old_tarih = odeme.tarih
            
            # Get new values
            odeme.odeme_turu = request.POST.get('odeme_turu')
            odeme.tutar = safe_decimal(request.POST.get('tutar', '0'))
            odeme.tarih = request.POST.get('tarih') or odeme.tarih
            odeme.aciklama = request.POST.get('aciklama', '')
            kasa_id = request.POST.get('kasa')
            
            # Basic validation
            if not odeme.odeme_turu or odeme.tutar <= 0 or not kasa_id:
                messages.error(request, 'Ödeme türü, tutar ve kasa zorunludur. Tutar pozitif olmalıdır.')
                return redirect('personel_detail', pk=personel_pk)
            
            # Get cash register
            kasa = Kasalar.objects.get(id=kasa_id)
            odeme.kasa = kasa
            
            # Save updated payment
            odeme.save()
            
            # Find and update existing cash register transaction or create a new one
            try:
                # Try to find the cash transaction by document number
                hareket = GenelKasaHareketi.objects.filter(belge_no=odeme.belge_no).first()
                
                if hareket:
                    # Update existing transaction
                    hareket.kasa = kasa
                    hareket.kategori = 'Personel Ödemesi'
                    hareket.gider_turu = odeme.odeme_turu
                    hareket.tutar = odeme.tutar
                    hareket.tarih = odeme.tarih
                    aciklama_text = f"{odeme.personel.PerAd} {odeme.personel.PerSoyad}"
                    if odeme.aciklama:
                        aciklama_text += f" - {odeme.aciklama}"
                    hareket.aciklama = aciklama_text
                    hareket.save()
                else:
                    # Create new transaction if none found
                    aciklama_text = f"{odeme.personel.PerAd} {odeme.personel.PerSoyad}"
                    if odeme.aciklama:
                        aciklama_text += f" - {odeme.aciklama}"
                    hareket = GenelKasaHareketi.objects.create(
                        kasa=kasa,
                        hareket_tipi='Gider',
                        kategori='Personel Ödemesi',
                        gider_turu=odeme.odeme_turu,
                        tutar=odeme.tutar,
                        tarih=odeme.tarih,
                        belge_no=odeme.belge_no,
                        aciklama=aciklama_text
                    )
            except Exception as e:
                # If there was an error updating the cash transaction, log it but don't fail
                print(f"Kasa hareketini güncelleme hatası: {str(e)}")
            
            messages.success(
                request, 
                f"{odeme.personel.PerAd} {odeme.personel.PerSoyad} personeli için {odeme.odeme_turu} ödemesi güncellendi."
            )
            
        except Exception as e:
            messages.error(request, f'Ödeme güncelleme hatası: {str(e)}')
    
    return redirect('personel_detail', pk=personel_pk)

def personel_odeme_delete(request, pk):
    """Delete a payment."""
    odeme = get_object_or_404(PersonelOdeme, pk=pk)
    personel_pk = odeme.personel.pk
    belge_no = odeme.belge_no  # Store for later use
    
    if request.method == 'POST':
        try:
            odeme_turu = odeme.odeme_turu
            
            # Try to delete associated cash register transaction
            try:
                hareket = GenelKasaHareketi.objects.filter(belge_no=belge_no).first()
                if hareket:
                    hareket.delete()
            except Exception as e:
                # Log but don't fail if deleting the associated transaction fails
                print(f"Kasa hareketini silme hatası: {str(e)}")
                
            # Delete the payment
            odeme.delete()
            
            messages.success(
                request, 
                f"{odeme_turu} ödemesi başarıyla silindi."
            )
            
        except Exception as e:
            messages.error(request, f'Ödeme silme hatası: {str(e)}')
    
    return redirect('personel_detail', pk=personel_pk) 