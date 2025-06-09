from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum, F
import xlwt
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from ..models import AracBilgileri, AracBakim, YeniAracBakim, AracUyari, Kasalar, ParaBirimleri, Personeller, GenelKasaHareketi, Seferler
from .helpers import register_ttf_fonts, turkish_safe_text, format_currency, get_first_two_words
from sefer_app.utils import get_firma_unvan

# Belge numarası üretici
def generate_document_number():
    today = datetime.now()
    year_month = f"{today.year}{today.month:02d}"
    prefix = f"BKM-{year_month}-"
    try:
        latest_bakim = YeniAracBakim.objects.filter(belge_no__startswith=prefix).order_by("-belge_no").first()
        if latest_bakim and latest_bakim.belge_no:
            last_num = int(latest_bakim.belge_no.split("-")[-1])
            return f"{prefix}{last_num + 1}"
    except Exception as e:
        print(f"Belge numarası oluşturulurken hata: {e}")
    return f"{prefix}1"

# Araç (Vehicle) views
def arac_list(request):
    try:
        # Base queryset for all vehicles
        araclar = AracBilgileri.objects.all()
        
        # Apply filters if provided
        arac_durumu = request.GET.get('arac_durumu', '')
        arac_tipi = request.GET.get('arac_tipi', '')
        arama = request.GET.get('arama', '')
        
        if arac_durumu:
            araclar = araclar.filter(arac_durumu=arac_durumu)
        
        if arac_tipi:
            araclar = araclar.filter(arac_tipi=arac_tipi)
        
        if arama:
            araclar = araclar.filter(
                models.Q(plaka__icontains=arama) | 
                models.Q(marka__icontains=arama) |
                models.Q(model__icontains=arama)
            )
        
        # Handle POST for export
        if request.method == 'POST':
            export_format = request.POST.get('export_format', '')
            if export_format == 'pdf':
                return export_arac_pdf(request, araclar)
            elif export_format == 'excel':
                return export_arac_excel(request, araclar)
        
        # Check for export parameter in GET as fallback
        export_format = request.GET.get('export', '')
        if export_format == 'pdf':
            return export_arac_pdf(request, araclar)
        elif export_format == 'excel':
            return export_arac_excel(request, araclar)
        
        # Calculate statistics for the info band
        toplam_arac_sayisi = AracBilgileri.objects.count()
        aktif_arac_sayisi = AracBilgileri.objects.filter(arac_durumu='Aktif').count()
        pasif_arac_sayisi = toplam_arac_sayisi - aktif_arac_sayisi
        
        # Count vehicles with active warnings
        uyari_sayisi = AracUyari.objects.filter(durum='aktif').values('arac').distinct().count()
        
        # Calculate total and average kilometers from trips
        # Query all trips that have distance values regardless of status
        tamamlanan_seferler = Seferler.objects.filter(mesafe__isnull=False)
        print(f"DEBUG: Found {tamamlanan_seferler.count()} trips with valid mesafe values")
        
        toplam_km = 0
        if tamamlanan_seferler.exists():
            # Sum up distances from all trips with valid distance values
            toplam_km = tamamlanan_seferler.aggregate(models.Sum('mesafe'))['mesafe__sum'] or 0
            print(f"DEBUG: Total KM: {toplam_km}")
            
            # Calculate average km per trip
            sefer_sayisi = tamamlanan_seferler.count()
            ortalama_kilometre = toplam_km / sefer_sayisi if sefer_sayisi > 0 else 0
            print(f"DEBUG: Average KM per trip: {ortalama_kilometre}")
        else:
            ortalama_kilometre = 0
            print("DEBUG: No trips with distance found")
            
        # Count maintenance-waiting vehicles
        bakim_bekleyen_sayisi = 0
        today = timezone.now().date()
        bakim_bekleyen = AracBakim.objects.filter(bir_sonraki_bakim_tarihi__lte=today).values('arac').distinct()
        bakim_bekleyen_sayisi = bakim_bekleyen.count()
    
    except Exception as e:
        print(f"Araçlar getirilirken hata: {e}")
        araclar = []
        aktif_arac_sayisi = 0
        pasif_arac_sayisi = 0
        uyari_sayisi = 0
        ortalama_kilometre = 0
        toplam_km = 0
        bakim_bekleyen_sayisi = 0
    
    context = {
        'araclar': araclar,
        'today': timezone.now().date(),
        'toplam_arac_sayisi': toplam_arac_sayisi,
        'aktif_arac_sayisi': aktif_arac_sayisi,
        'pasif_arac_sayisi': pasif_arac_sayisi,
        'uyari_sayisi': uyari_sayisi,
        'ortalama_kilometre': ortalama_kilometre,
        'toplam_km': toplam_km,
        'bakim_bekleyen_sayisi': bakim_bekleyen_sayisi
    }
    return render(request, 'sefer_app/arac_list.html', context)

def export_arac_pdf(request, araclar_queryset=None):
    """Generate PDF report with vehicle list."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Use provided queryset or get all vehicles
    if araclar_queryset is None:
        araclar = AracBilgileri.objects.all().order_by('plaka')
    else:
        araclar = araclar_queryset
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="arac_listesi.pdf"'
    
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
    elements.append(Paragraph(turkish_safe_text("ARAÇ LİSTESİ"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Create table data
    data = [
        [
            turkish_safe_text("Plaka"), 
            turkish_safe_text("Marka"),
            turkish_safe_text("Model"), 
            turkish_safe_text("Model Yılı"), 
            turkish_safe_text("Araç Tipi"), 
            turkish_safe_text("Yakıt"),
            turkish_safe_text("Şoför"),
            turkish_safe_text("Durum")
        ]
    ]
    
    # Add vehicle data rows
    for arac in araclar:
        # Format driver name if assigned
        sofor = f"{arac.atanmis_sofor.PerAd} {arac.atanmis_sofor.PerSoyad}" if arac.atanmis_sofor else "-"
        
        # Format status
        durum = turkish_safe_text(arac.arac_durumu)
        
        # Add row to table data
        data.append([
            arac.plaka,
            turkish_safe_text(arac.marka or "-"),
            turkish_safe_text(arac.model or "-"),
            str(arac.model_yili or "-"),
            turkish_safe_text(arac.arac_tipi or "-"),
            turkish_safe_text(arac.yakit_tipi or "-"),
            turkish_safe_text(sofor),
            durum
        ])
    
    # Calculate column widths
    col_widths = [2.5*cm, 3*cm, 3*cm, 2*cm, 3*cm, 2*cm, 3.5*cm, 2*cm]
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

def export_arac_excel(request, araclar_queryset=None):
    """Export vehicle list as Excel."""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="arac_listesi.xls"'
    
    # Use provided queryset or get all vehicles
    if araclar_queryset is None:
        araclar = AracBilgileri.objects.all().order_by('plaka')
    else:
        araclar = araclar_queryset
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Araç Listesi')
    
    # Sheet header
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Add title to Excel
    ws.write(row_num, 0, get_firma_unvan(), font_style)
    row_num += 1
    
    # Add report title
    ws.write(row_num, 0, "Araç Listesi", font_style)
    row_num += 1
    
    # Add report generation date
    ws.write(row_num, 0, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", font_style)
    row_num += 2  # Add an extra row for spacing
    
    # Column headers
    columns = ['Plaka', 'Marka', 'Model', 'Model Yılı', 'Araç Tipi', 'Yakıt Tipi', 
               'Motor No', 'Şasi No', 'İlk Kilometre', 'Lastik Ölçüleri', 'Atanmış Şoför', 'Durum']
    
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    # Sheet body
    font_style = xlwt.XFStyle()
    
    for arac in araclar:
        row_num += 1
        
        # Format driver name if assigned
        sofor = f"{arac.atanmis_sofor.PerAd} {arac.atanmis_sofor.PerSoyad}" if arac.atanmis_sofor else "-"
        
        # Add data to row
        col_num = 0
        ws.write(row_num, col_num, arac.plaka); col_num += 1
        ws.write(row_num, col_num, arac.marka or "-"); col_num += 1
        ws.write(row_num, col_num, arac.model or "-"); col_num += 1
        ws.write(row_num, col_num, arac.model_yili or "-"); col_num += 1
        ws.write(row_num, col_num, arac.arac_tipi or "-"); col_num += 1
        ws.write(row_num, col_num, arac.yakit_tipi or "-"); col_num += 1
        ws.write(row_num, col_num, arac.motor_no or "-"); col_num += 1
        ws.write(row_num, col_num, arac.sasi_no or "-"); col_num += 1
        ws.write(row_num, col_num, arac.ilk_kilometre or 0); col_num += 1
        ws.write(row_num, col_num, arac.lastik_olculeri or "-"); col_num += 1
        ws.write(row_num, col_num, sofor); col_num += 1
        ws.write(row_num, col_num, arac.arac_durumu)
    
    wb.save(response)
    return response

def arac_detail(request, pk):
    try:
        arac = get_object_or_404(AracBilgileri, pk=pk)
        bakimlar = AracBakim.objects.filter(arac=arac)
        uyarilar = AracUyari.objects.filter(arac=arac)
        
        # Get all trips for this vehicle
        seferler = Seferler.objects.filter(arac=arac).order_by('-cikis_tarihi')
        
        # Get the latest trip with the vehicle (regardless of status)
        son_sefer = Seferler.objects.filter(arac=arac).order_by('-cikis_tarihi').first()
    except Exception as e:
        print(f"Araç detayları getirilirken hata: {e}")
        arac = None
        bakimlar = []
        uyarilar = []
        son_sefer = None
        seferler = []
    
    context = {
        'arac': arac,
        'bakimlar': bakimlar,
        'uyarilar': uyarilar,
        'son_sefer': son_sefer,
        'seferler': seferler,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/arac_detail.html', context)

def arac_detail_pdf(request, pk):
    """Generate PDF report with vehicle details."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    arac = get_object_or_404(AracBilgileri, pk=pk)
    
    # Get related objects
    bakimlar = AracBakim.objects.filter(arac=arac)
    uyarilar = AracUyari.objects.filter(arac=arac)
    seferler = Seferler.objects.filter(arac=arac).order_by('-cikis_tarihi')[:10]  # Limit to recent 10
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="arac_{pk}_detay.pdf"'
    
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
    elements.append(Paragraph(turkish_safe_text(f"ARAÇ DETAY: {arac.plaka}"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Vehicle general information
    elements.append(Paragraph(turkish_safe_text("Genel Bilgiler"), subtitle_style))
    
    # Vehicle info table
    genel_data = [
        [turkish_safe_text("Plaka:"), arac.plaka],
        [turkish_safe_text("Marka:"), turkish_safe_text(arac.marka or "-")],
        [turkish_safe_text("Model:"), turkish_safe_text(arac.model or "-")],
        [turkish_safe_text("Model Yılı:"), str(arac.model_yili or "-")],
        [turkish_safe_text("Araç Tipi:"), turkish_safe_text(arac.arac_tipi or "-")],
        [turkish_safe_text("Yakıt Tipi:"), turkish_safe_text(arac.yakit_tipi or "-")],
        [turkish_safe_text("Motor No:"), arac.motor_no or "-"],
        [turkish_safe_text("Şasi No:"), arac.sasi_no or "-"],
        [turkish_safe_text("İlk Kilometre:"), str(arac.ilk_kilometre or "0")],
        [turkish_safe_text("Lastik Ölçüleri:"), turkish_safe_text(arac.lastik_olculeri or "-")],
        [turkish_safe_text("Atanmış Şoför:"), turkish_safe_text(get_first_two_words(f"{arac.atanmis_sofor.PerAd} {arac.atanmis_sofor.PerSoyad}") if arac.atanmis_sofor else "-")],
        [turkish_safe_text("Durum:"), turkish_safe_text(arac.arac_durumu)],
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
    
    # Add maintenance information
    if bakimlar.exists():
        elements.append(Paragraph(turkish_safe_text("Bakım Bilgileri"), subtitle_style))
        bakim_data = [
            [
                turkish_safe_text("Bakım Tipi"),
                turkish_safe_text("Son Bakım Tarihi"),
                turkish_safe_text("Son Bakım KM"),
                turkish_safe_text("Sonraki Bakım Tarihi"),
                turkish_safe_text("Sonraki Bakım KM")
            ]
        ]
        
        for bakim in bakimlar:
            bakim_data.append([
                turkish_safe_text(bakim.bakim_turu or "-"),
                bakim.bakim_tarihi.strftime('%d.%m.%Y') if bakim.bakim_tarihi else "-", 
                "-", # No son_bakim_kilometre field exists in AracBakim model
                bakim.bir_sonraki_bakim_tarihi.strftime('%d.%m.%Y') if bakim.bir_sonraki_bakim_tarihi else "-",
                str(bakim.bir_sonraki_bakim_km or "-")
            ])
        
        table = Table(bakim_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm], repeatRows=1)
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
        elements.append(Spacer(1, 0.5*cm))
    
    # Warnings section removed as requested
    
    # Add recent trips information
    if seferler.exists():
        elements.append(Paragraph(turkish_safe_text("Son Seferler"), subtitle_style))
        sefer_data = [
            [
                turkish_safe_text("Sefer Kodu"),
                turkish_safe_text("Rota"),
                turkish_safe_text("Çıkış Tarihi"),
                turkish_safe_text("Mesafe"),
                turkish_safe_text("Durum")
            ]
        ]
        
        for sefer in seferler:
            rota = f"{sefer.baslangic_sehri.sehir_adi if sefer.baslangic_sehri else '-'} → {sefer.bitis_sehri.sehir_adi if sefer.bitis_sehri else '-'}"
            sefer_data.append([
                sefer.sefer_kodu,
                turkish_safe_text(rota),
                sefer.cikis_tarihi.strftime('%d.%m.%Y') if sefer.cikis_tarihi else "-",
                f"{sefer.mesafe} km" if sefer.mesafe else "-",
                turkish_safe_text(sefer.durum)
            ])
        
        table = Table(sefer_data, colWidths=[3*cm, 7*cm, 3*cm, 2*cm, 3*cm], repeatRows=1)
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

def arac_detail_excel(request, pk):
    """Export vehicle details as Excel."""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="arac_{pk}_detay.xls"'
    
    # Get vehicle and related data
    arac = get_object_or_404(AracBilgileri, pk=pk)
    bakimlar = AracBakim.objects.filter(arac=arac).order_by('-bakim_tarihi')
    uyarilar = AracUyari.objects.filter(arac=arac).order_by('-olusturma_tarihi')
    seferler = Seferler.objects.filter(arac=arac).order_by('-cikis_tarihi')[:20]  # Limit to recent 20
    
    wb = xlwt.Workbook(encoding='utf-8')
    
    # Vehicle details sheet
    ws_arac = wb.add_sheet('Araç Bilgileri')
    
    # Header style
    header_style = xlwt.XFStyle()
    header_style.font.bold = True
    
    # Title
    row_num = 0
    ws_arac.write(row_num, 0, get_firma_unvan(), header_style)
    row_num += 1
    ws_arac.write(row_num, 0, f"Araç Detay: {arac.plaka}", header_style)
    row_num += 1
    ws_arac.write(row_num, 0, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", header_style)
    row_num += 2  # Add spacing
    
    # Vehicle details
    row_num += 1
    ws_arac.write(row_num, 0, "Plaka:", header_style)
    ws_arac.write(row_num, 1, arac.plaka)
    
    row_num += 1
    ws_arac.write(row_num, 0, "Marka / Model:", header_style)
    ws_arac.write(row_num, 1, f"{arac.marka} {arac.model}")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Model Yılı:", header_style)
    ws_arac.write(row_num, 1, arac.model_yili or "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Araç Tipi:", header_style)
    ws_arac.write(row_num, 1, arac.arac_tipi or "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Yakıt Tipi:", header_style)
    ws_arac.write(row_num, 1, arac.yakit_tipi or "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Motor No:", header_style)
    ws_arac.write(row_num, 1, arac.motor_no or "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Şasi No:", header_style)
    ws_arac.write(row_num, 1, arac.sasi_no or "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "İlk Kilometre:", header_style)
    ws_arac.write(row_num, 1, arac.ilk_kilometre or "0")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Atanmış Şoför:", header_style)
    ws_arac.write(row_num, 1, f"{arac.atanmis_sofor.PerAd} {arac.atanmis_sofor.PerSoyad}" if arac.atanmis_sofor else "-")
    
    row_num += 1
    ws_arac.write(row_num, 0, "Durum:", header_style)
    ws_arac.write(row_num, 1, arac.arac_durumu)
    
    # Maintenance sheet
    if bakimlar.exists():
        ws_bakim = wb.add_sheet('Bakımlar')
        
        # Headers
        row_num = 0
        ws_bakim.write(row_num, 0, "Tarih", header_style)
        ws_bakim.write(row_num, 1, "Bakım Türü", header_style)
        ws_bakim.write(row_num, 2, "Yapılan İşlemler", header_style)
        ws_bakim.write(row_num, 3, "Maliyet", header_style)
        ws_bakim.write(row_num, 4, "Sonraki Bakım", header_style)
        
        # Data
        for bakim in bakimlar:
            row_num += 1
            
            # Format date and values
            bakim_tarihi = bakim.bakim_tarihi.strftime('%d.%m.%Y') if bakim.bakim_tarihi else "-"
            sonraki_bakim = "-"
            if bakim.bir_sonraki_bakim_tarihi:
                sonraki_bakim = bakim.bir_sonraki_bakim_tarihi.strftime('%d.%m.%Y')
            elif bakim.bir_sonraki_bakim_km:
                sonraki_bakim = f"{bakim.bir_sonraki_bakim_km} km"
            
            # Add row
            ws_bakim.write(row_num, 0, bakim_tarihi)
            ws_bakim.write(row_num, 1, bakim.bakim_turu)
            ws_bakim.write(row_num, 2, bakim.yapilan_islemler or "-")
            ws_bakim.write(row_num, 3, float(bakim.maliyet) if bakim.maliyet else 0)
            ws_bakim.write(row_num, 4, sonraki_bakim)
    
    # Warnings sheet
    if uyarilar.exists():
        ws_uyari = wb.add_sheet('Uyarılar')
        
        # Headers
        row_num = 0
        ws_uyari.write(row_num, 0, "Tarih", header_style)
        ws_uyari.write(row_num, 1, "Tür", header_style)
        ws_uyari.write(row_num, 2, "Mesaj", header_style)
        ws_uyari.write(row_num, 3, "Son Tarih", header_style)
        ws_uyari.write(row_num, 4, "Durum", header_style)
        
        # Data
        for uyari in uyarilar:
            row_num += 1
            
            # Add row
            ws_uyari.write(row_num, 0, uyari.olusturma_tarihi.strftime('%d.%m.%Y') if uyari.olusturma_tarihi else "-")
            ws_uyari.write(row_num, 1, uyari.get_uyari_turu_display() or "-")
            ws_uyari.write(row_num, 2, uyari.uyari_mesaji or "-")
            ws_uyari.write(row_num, 3, uyari.son_tarih.strftime('%d.%m.%Y') if uyari.son_tarih else "-")
            ws_uyari.write(row_num, 4, uyari.get_durum_display() or "-")
    
    # Trips sheet
    if seferler.exists():
        ws_sefer = wb.add_sheet('Seferler')
        
        # Headers
        row_num = 0
        ws_sefer.write(row_num, 0, "Sefer Kodu", header_style)
        ws_sefer.write(row_num, 1, "Çıkış Tarihi", header_style)
        ws_sefer.write(row_num, 2, "Varış Tarihi", header_style)
        ws_sefer.write(row_num, 3, "Rota", header_style)
        ws_sefer.write(row_num, 4, "Şoför", header_style)
        ws_sefer.write(row_num, 5, "Firma", header_style)
        ws_sefer.write(row_num, 6, "Durum", header_style)
        
        # Data
        for sefer in seferler:
            row_num += 1
            
            # Format rota
            rota = "-"
            if sefer.guzergah:
                rota = sefer.guzergah
            elif sefer.baslangic_sehri and sefer.bitis_sehri:
                rota = f"{sefer.baslangic_sehri.sehir_adi} → {sefer.bitis_sehri.sehir_adi}"
            
            # Add row
            ws_sefer.write(row_num, 0, sefer.sefer_kodu)
            ws_sefer.write(row_num, 1, sefer.cikis_tarihi.strftime('%d.%m.%Y') if sefer.cikis_tarihi else "-")
            ws_sefer.write(row_num, 2, sefer.varis_tarihi.strftime('%d.%m.%Y') if sefer.varis_tarihi else "-")
            ws_sefer.write(row_num, 3, rota)
            ws_sefer.write(row_num, 4, f"{sefer.personel.PerAd} {sefer.personel.PerSoyad}" if sefer.personel else "-")
            ws_sefer.write(row_num, 5, sefer.firma.FirmaAdi if sefer.firma else "-")
            ws_sefer.write(row_num, 6, sefer.durum)
    
    wb.save(response)
    return response

def arac_create(request):
    if request.method == 'POST':
        try:
            plaka = request.POST.get('plaka')
            arac_tipi = request.POST.get('arac_tipi')
            kullanim_sekli = request.POST.get('kullanim_sekli')
            arac_durumu = request.POST.get('arac_durumu')
            marka = request.POST.get('marka')
            model = request.POST.get('model')
            model_yili = request.POST.get('model_yili')
            yakit_tipi = request.POST.get('yakit_tipi')
            motor_no = request.POST.get('motor_no')
            sasi_no = request.POST.get('sasi_no')
            ilk_kilometre = request.POST.get('ilk_kilometre')
            lastik_olculeri = request.POST.get('lastik_olculeri')
            atanmis_sofor_id = request.POST.get('atanmis_sofor')
            
            atanmis_sofor = None
            if atanmis_sofor_id:
                atanmis_sofor = Personeller.objects.get(id=atanmis_sofor_id)
            
            arac = AracBilgileri(
                plaka=plaka,
                arac_tipi=arac_tipi,
                kullanim_sekli=kullanim_sekli,
                arac_durumu=arac_durumu,
                marka=marka,
                model=model,
                model_yili=model_yili if model_yili else None,
                yakit_tipi=yakit_tipi,
                motor_no=motor_no,
                sasi_no=sasi_no,
                ilk_kilometre=ilk_kilometre if ilk_kilometre else 0,
                lastik_olculeri=lastik_olculeri,
                atanmis_sofor=atanmis_sofor
            )
            arac.save()
            
            messages.success(request, "Araç başarıyla kaydedildi.")
            return redirect('arac_list')
        
        except Exception as e:
            print(f"Araç oluşturulurken hata: {e}")
            messages.error(request, f"Araç kaydedilirken hata oluştu: {e}")
    
    try:
        personeller = Personeller.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        personeller = []
    
    context = {
        'personeller': personeller,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/arac_form.html', context)

def arac_update(request, pk):
    try:
        arac = get_object_or_404(AracBilgileri, pk=pk)
    except Exception as e:
        print(f"Güncellenecek araç bulunamadı: {e}")
        arac = None
        return redirect('arac_list')
    
    if request.method == 'POST':
        try:
            arac.plaka = request.POST.get('plaka')
            arac.arac_tipi = request.POST.get('arac_tipi')
            arac.kullanim_sekli = request.POST.get('kullanim_sekli')
            arac.arac_durumu = request.POST.get('arac_durumu')
            arac.marka = request.POST.get('marka')
            arac.model = request.POST.get('model')
            arac.model_yili = request.POST.get('model_yili') or None
            arac.yakit_tipi = request.POST.get('yakit_tipi')
            arac.motor_no = request.POST.get('motor_no')
            arac.sasi_no = request.POST.get('sasi_no')
            arac.ilk_kilometre = request.POST.get('ilk_kilometre') or 0
            arac.lastik_olculeri = request.POST.get('lastik_olculeri')
            
            atanmis_sofor_id = request.POST.get('atanmis_sofor')
            if atanmis_sofor_id:
                arac.atanmis_sofor = Personeller.objects.get(id=atanmis_sofor_id)
            else:
                arac.atanmis_sofor = None
            
            arac.save()
            
            messages.success(request, "Araç başarıyla güncellendi.")
            return redirect('arac_detail', pk=arac.id)
        
        except Exception as e:
            print(f"Araç güncellenirken hata: {e}")
            messages.error(request, f"Araç güncellenirken hata oluştu: {e}")
    
    try:
        personeller = Personeller.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        personeller = []
    
    context = {
        'arac': arac,
        'personeller': personeller,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/arac_form.html', context)

def arac_delete(request, pk):
    try:
        arac = get_object_or_404(AracBilgileri, pk=pk)
        if request.method == 'POST':
            arac.delete()
            messages.success(request, "Araç başarıyla silindi.")
            return redirect('arac_list')
    except Exception as e:
        print(f"Araç silinirken hata: {e}")
        arac = None
    
    context = {
        'arac': arac
    }
    return render(request, 'sefer_app/arac_confirm_delete.html', context)

# Bakım (Maintenance) views
def bakim_list(request):
    bakimlar = AracBakim.objects.all().order_by('-bakim_tarihi')
    araclar = AracBilgileri.objects.all()
    
    # Handle POST for export
    if request.method == 'POST':
        export_format = request.POST.get('export_format', '')
        if export_format == 'pdf':
            return export_bakim_pdf(request, bakimlar)
        elif export_format == 'excel':
            return export_bakim_excel(request, bakimlar)
    
    # Check for export parameter in GET as fallback
    export_format = request.GET.get('export', '')
    if export_format == 'pdf':
        return export_bakim_pdf(request, bakimlar)
    elif export_format == 'excel':
        return export_bakim_excel(request, bakimlar)
    
    # Apply filters if provided
    arac_id = request.GET.get('arac', '')
    bakim_turu = request.GET.get('bakim_turu', '')
    arama = request.GET.get('arama', '')
    
    if arac_id:
        bakimlar = bakimlar.filter(arac_id=arac_id)
    
    if bakim_turu:
        bakimlar = bakimlar.filter(bakim_turu=bakim_turu)
    
    if arama:
        # Araç plakasına göre filtreleme
        arac_ids = AracBilgileri.objects.filter(plaka__icontains=arama).values_list('id', flat=True)
        bakimlar = bakimlar.filter(models.Q(arac__id__in=arac_ids) | models.Q(bakim_turu__icontains=arama))
    
    # Get distinct types for filter dropdown
    bakim_turleri = AracBakim.objects.exclude(bakim_turu__exact='').values_list('bakim_turu', flat=True).distinct()
    
    # Calculate stats for info band
    gecmis_bakim_sayisi = AracBakim.objects.filter(bir_sonraki_bakim_tarihi__lt=timezone.now().date()).count()
    bugun_bakim_sayisi = AracBakim.objects.filter(bir_sonraki_bakim_tarihi=timezone.now().date()).count()
    yakinda_bakim_sayisi = AracBakim.objects.filter(
        bir_sonraki_bakim_tarihi__gt=timezone.now().date(),
        bir_sonraki_bakim_tarihi__lte=timezone.now().date() + timedelta(days=30)
    ).count()
    
    context = {
        'bakimlar': bakimlar,
        'araclar': araclar,
        'bakim_turleri': bakim_turleri,
        'today': timezone.now().date(),
        'gecmis_bakim_sayisi': gecmis_bakim_sayisi,
        'bugun_bakim_sayisi': bugun_bakim_sayisi,
        'yakinda_bakim_sayisi': yakinda_bakim_sayisi,
        'toplam_bakim_sayisi': bakimlar.count()
    }
    return render(request, 'sefer_app/bakim_list.html', context)

def export_bakim_pdf(request, bakimlar_queryset=None):
    """Generate PDF report with maintenance list."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Use provided queryset or get all maintenance records
    if bakimlar_queryset is None:
        bakimlar = AracBakim.objects.all().order_by('-bakim_tarihi')
    else:
        bakimlar = bakimlar_queryset
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bakim_listesi.pdf"'
    
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
    elements.append(Paragraph(turkish_safe_text("ARAÇ BAKIM LİSTESİ"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Create table data
    data = [
        [
            turkish_safe_text("Araç Plaka"),
            turkish_safe_text("Bakım Tipi"),
            turkish_safe_text("Bakım Tarihi"),
            turkish_safe_text("Maliyet"),
            turkish_safe_text("Sonraki Bakım Tarihi"),
            turkish_safe_text("Sonraki Bakım KM"),
            turkish_safe_text("Durum")
        ]
    ]
    
    # Get today's date for status comparison
    today = timezone.now().date()
    
    # Add maintenance data rows
    for bakim in bakimlar:
        # Calculate status
        if bakim.bir_sonraki_bakim_tarihi:
            if bakim.bir_sonraki_bakim_tarihi < today:
                durum = turkish_safe_text("Gecikmiş")
            elif bakim.bir_sonraki_bakim_tarihi == today:
                durum = turkish_safe_text("Bugün")
            elif bakim.bir_sonraki_bakim_tarihi <= today + timedelta(days=30):
                durum = turkish_safe_text("Yakında")
            else:
                durum = turkish_safe_text("Güncel")
        else:
            durum = turkish_safe_text("Belirsiz")
        
        # Add row to table data
        data.append([
            bakim.arac.plaka if bakim.arac else "-",
            turkish_safe_text(bakim.bakim_turu or "-"),
            bakim.bakim_tarihi.strftime('%d.%m.%Y') if bakim.bakim_tarihi else "-",
            format_currency(bakim.maliyet) if bakim.maliyet else "-",
            bakim.bir_sonraki_bakim_tarihi.strftime('%d.%m.%Y') if bakim.bir_sonraki_bakim_tarihi else "-",
            str(bakim.bir_sonraki_bakim_km or "-"),
            durum
        ])
    
    # Calculate column widths
    col_widths = [2.5*cm, 3*cm, 3*cm, 2.5*cm, 3*cm, 2.5*cm, 2.5*cm]
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

def export_bakim_excel(request, bakimlar_queryset=None):
    """Export maintenance list as Excel."""
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="bakim_listesi.xls"'
    
    # Use provided queryset or get all maintenance records
    if bakimlar_queryset is None:
        bakimlar = AracBakim.objects.all().order_by('-bakim_tarihi')
    else:
        bakimlar = bakimlar_queryset
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Bakım Listesi')
    
    # Sheet header
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    
    # Add title to Excel
    ws.write(row_num, 0, get_firma_unvan(), font_style)
    row_num += 1
    
    # Add report title
    ws.write(row_num, 0, "Araç Bakım Listesi", font_style)
    row_num += 1
    
    # Add report generation date
    ws.write(row_num, 0, f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", font_style)
    row_num += 2  # Add an extra row for spacing
    
    # Column headers
    columns = ['Araç Plaka', 'Marka', 'Model', 'Bakım Tipi', 'Son Bakım Tarihi', 'Son Bakım KM', 
               'Sonraki Bakım Tarihi', 'Sonraki Bakım KM', 'Notlar', 'Durum']
    
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)
    
    # Get today's date for status comparison
    today = timezone.now().date()
    
    # Sheet body
    font_style = xlwt.XFStyle()
    
    for bakim in bakimlar:
        row_num += 1
        
        # Calculate status
        if bakim.bir_sonraki_bakim_tarihi:
            if bakim.bir_sonraki_bakim_tarihi < today:
                durum = "Gecikmiş"
            elif bakim.bir_sonraki_bakim_tarihi == today:
                durum = "Bugün"
            elif bakim.bir_sonraki_bakim_tarihi <= today + timedelta(days=30):
                durum = "Yakında"
            else:
                durum = "Güncel"
        else:
            durum = "Belirsiz"
        
        # Add data to row
        col_num = 0
        ws.write(row_num, col_num, bakim.arac.plaka if bakim.arac else "-"); col_num += 1
        ws.write(row_num, col_num, bakim.arac.marka if bakim.arac else "-"); col_num += 1
        ws.write(row_num, col_num, bakim.arac.model if bakim.arac else "-"); col_num += 1
        ws.write(row_num, col_num, bakim.bakim_turu or "-"); col_num += 1
        ws.write(row_num, col_num, bakim.bakim_tarihi.strftime('%d.%m.%Y') if bakim.bakim_tarihi else "-"); col_num += 1
        ws.write(row_num, col_num, "0"); col_num += 1  # No son_bakim_kilometre field exists in AracBakim model
        ws.write(row_num, col_num, bakim.bir_sonraki_bakim_tarihi.strftime('%d.%m.%Y') if bakim.bir_sonraki_bakim_tarihi else "-"); col_num += 1
        ws.write(row_num, col_num, bakim.bir_sonraki_bakim_km or 0); col_num += 1
        ws.write(row_num, col_num, bakim.notlar or "-"); col_num += 1
        ws.write(row_num, col_num, durum)
    
    wb.save(response)
    return response

def bakim_create(request):
    if request.method == 'POST':
        try:
            arac_id = request.POST.get('arac')
            bakim_turu = request.POST.get('bakim_turu')
            bakim_tarihi = request.POST.get('bakim_tarihi')
            yapilan_islemler = request.POST.get('yapilan_islemler')
            maliyet = request.POST.get('maliyet')
            para_birimi = request.POST.get('para_birimi', 'TRY')
            kasa_id = request.POST.get('kasa')
            bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km')
            bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi')
            notlar = request.POST.get('notlar', '')
            
            # Get related objects
            arac = AracBilgileri.objects.get(id=arac_id)
            kasa = None
            if kasa_id:
                kasa = Kasalar.objects.get(id=kasa_id)
            
            # Create the maintenance record
            bakim = AracBakim(
                arac=arac,
                bakim_turu=bakim_turu,
                bakim_tarihi=bakim_tarihi,
                yapilan_islemler=yapilan_islemler,
                maliyet=maliyet,
                para_birimi=para_birimi,
                kasa=kasa,
                bir_sonraki_bakim_km=bir_sonraki_bakim_km if bir_sonraki_bakim_km else None,
                bir_sonraki_bakim_tarihi=bir_sonraki_bakim_tarihi if bir_sonraki_bakim_tarihi else None,
                notlar=notlar
            )
            bakim.save()
            
            messages.success(request, "Bakım kaydı başarıyla oluşturuldu.")
            return redirect('bakim_list')
            
        except Exception as e:
            print(f"Bakım kaydı oluşturulurken hata: {e}")
            messages.error(request, f"Bakım kaydı oluşturulurken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar = []
        kasalar = []
    
    context = {
        'araclar': araclar,
        'kasalar': kasalar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/bakim_form.html', context)

def bakim_update(request, pk):
    try:
        bakim = get_object_or_404(AracBakim, pk=pk)
    except Exception as e:
        print(f"Güncellenmek istenen bakım bulunamadı: {e}")
        return redirect('bakim_list')
    
    if request.method == 'POST':
        try:
            arac_id = request.POST.get('arac')
            bakim.bakim_turu = request.POST.get('bakim_turu')
            bakim.bakim_tarihi = request.POST.get('bakim_tarihi')
            bakim.yapilan_islemler = request.POST.get('yapilan_islemler')
            bakim.maliyet = request.POST.get('maliyet')
            bakim.para_birimi = request.POST.get('para_birimi', 'TRY')
            kasa_id = request.POST.get('kasa')
            bakim.bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km') or None
            bakim.bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi') or None
            bakim.notlar = request.POST.get('notlar', '')
            
            # Update related objects
            bakim.arac = AracBilgileri.objects.get(id=arac_id)
            if kasa_id:
                bakim.kasa = Kasalar.objects.get(id=kasa_id)
            else:
                bakim.kasa = None
            
            bakim.save()
            
            messages.success(request, "Bakım kaydı başarıyla güncellendi.")
            return redirect('bakim_list')
            
        except Exception as e:
            print(f"Bakım kaydı güncellenirken hata: {e}")
            messages.error(request, f"Bakım kaydı güncellenirken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar = []
        kasalar = []
    
    context = {
        'bakim': bakim,
        'araclar': araclar,
        'kasalar': kasalar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/bakim_form.html', context)

def bakim_delete(request, pk):
    try:
        bakim = get_object_or_404(AracBakim, pk=pk)
        if request.method == 'POST':
            bakim.delete()
            messages.success(request, "Bakım kaydı başarıyla silindi.")
            return redirect('bakim_list')
    except Exception as e:
        print(f"Bakım kaydı silinirken hata: {e}")
        bakim = None
    
    context = {
        'bakim': bakim
    }
    return render(request, 'sefer_app/bakim_confirm_delete.html', context)

# Yeni Bakım views
def yeni_bakim_list(request):
    try:
        bakimlar = YeniAracBakim.objects.all().order_by('-bakim_tarihi')
    except Exception as e:
        print(f"Yeni bakım kayıtları getirilirken hata: {e}")
        bakimlar = []
    
    context = {
        'bakimlar': bakimlar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/yeni_bakim_list.html', context)

def yeni_bakim_create(request):
    if request.method == "POST":
        try:
            # Form alanlarını al
            arac_id = request.POST.get("arac")
            bakim_turu = request.POST.get("bakim_turu")
            bakim_tarihi = request.POST.get("bakim_tarihi")
            kilometre = request.POST.get("km")
            yapilan_islemler = request.POST.get("yapilan_islemler", "")
            maliyet = request.POST.get("maliyet", "0").replace(",", ".")
            para_birimi = request.POST.get("para_birimi", "TRY")
            bir_sonraki_bakim_km = request.POST.get("bir_sonraki_bakim_km", "")
            bir_sonraki_bakim_tarihi = request.POST.get("bir_sonraki_bakim_tarihi", "")
            notlar = request.POST.get("notlar", "")
            kur = request.POST.get("kur", "1.0").replace(",", ".")

            # Zorunlu alan kontrolleri
            if not arac_id:
                messages.error(request, "Araç seçimi zorunludur.")
                return redirect("yeni_bakim_create")

            if not bakim_turu:
                messages.error(request, "Bakım türü zorunludur.")
                return redirect("yeni_bakim_create")

            if not bakim_tarihi:
                messages.error(request, "Bakım tarihi zorunludur.")
                return redirect("yeni_bakim_create")

            # Maliyet & kur hesaplaması
            try:
                maliyet_float = float(maliyet)
                kur_float = float(kur)
                maliyet_eur = maliyet_float / kur_float if para_birimi != "EUR" else maliyet_float
            except ValueError:
                messages.error(request, "Maliyet ve kur değerleri geçerli sayılar olmalıdır.")
                return redirect("yeni_bakim_create")

            # Tarihi datetime formatına çevir
            try:
                bakim_tarihi_obj = datetime.strptime(bakim_tarihi, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Bakım tarihi geçerli bir formatta değil (YYYY-AA-GG).")
                return redirect("yeni_bakim_create")

            # İlgili kayıtları getir
            try:
                arac = AracBilgileri.objects.get(id=arac_id)
            except AracBilgileri.DoesNotExist:
                messages.error(request, "Seçilen araç bulunamadı.")
                return redirect("yeni_bakim_create")

            # Belge no üret
            belge_no = generate_document_number()

            # Sayısal ve tarih alanlarını hazırla
            km_value = int(kilometre) if kilometre and kilometre.strip().isdigit() else None
            next_km_value = int(bir_sonraki_bakim_km) if bir_sonraki_bakim_km and bir_sonraki_bakim_km.strip().isdigit() else None

            try:
                next_date_value = datetime.strptime(bir_sonraki_bakim_tarihi, "%Y-%m-%d").date() if bir_sonraki_bakim_tarihi else None
            except ValueError:
                next_date_value = None

            # Yeni bakım kaydını oluştur
            YeniAracBakim.objects.create(
                arac=arac,
                bakim_turu=bakim_turu,
                bakim_tarihi=bakim_tarihi_obj,
                kilometre=km_value,
                yapilan_islemler=yapilan_islemler,
                maliyet=maliyet_float,
                para_birimi=para_birimi,
                kur=kur_float,
                maliyet_eur=maliyet_eur,
                kasa=None,
                kasa_hareketi=None,
                belge_no=belge_no,
                bir_sonraki_bakim_km=next_km_value,
                bir_sonraki_bakim_tarihi=next_date_value,
                notlar=notlar
            )

            messages.success(request, "Yeni bakım kaydı başarıyla oluşturuldu.")
            return redirect("bakim_list")

        except Exception as e:
            import traceback
            print(f"Hata: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Yeni bakım oluşturulurken hata oluştu: {e}")
            return redirect("yeni_bakim_create")

    # GET isteği - formu göster
    try:
        araclar = AracBilgileri.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar, para_birimleri = [], []

    context = {
        "araclar": araclar,
        "para_birimleri": para_birimleri,
        "today": timezone.now().date(),
        "belge_no": generate_document_number()
    }
    return render(request, "sefer_app/yeni_bakim_form.html", context)

def yeni_bakim_update(request, pk):
    try:
        bakim = get_object_or_404(YeniAracBakim, pk=pk)
    except Exception as e:
        print(f"Güncellenecek yeni bakım kaydı bulunamadı: {e}")
        return redirect("bakim_list")
    
    if request.method == "POST":
        try:
            # Form değerlerini al
            arac_id = request.POST.get("arac")
            bakim_turu = request.POST.get("bakim_turu")
            bakim_tarihi = request.POST.get("bakim_tarihi")
            kilometre = request.POST.get("kilometre")
            yapilan_islemler = request.POST.get("yapilan_islemler", "")
            maliyet = request.POST.get("maliyet", "0").replace(",", ".")
            para_birimi = request.POST.get("para_birimi", "TRY")
            kur = request.POST.get("kur", "1.0").replace(",", ".")
            bir_sonraki_bakim_km = request.POST.get("bir_sonraki_bakim_km", "")
            bir_sonraki_bakim_tarihi = request.POST.get("bir_sonraki_bakim_tarihi", "")
            notlar = request.POST.get("notlar", "")
            
            # Sayısal değerleri işle
            try:
                maliyet_float = float(maliyet)
                kur_float = float(kur)
                maliyet_eur = maliyet_float / kur_float if para_birimi != "EUR" else maliyet_float
            except ValueError:
                messages.error(request, "Maliyet ve kur değerleri geçerli sayılar olmalıdır.")
                return redirect("yeni_bakim_update", pk=pk)
            
            # Tarihi işle
            try:
                bakim_tarihi_obj = datetime.strptime(bakim_tarihi, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Bakım tarihi geçerli bir formatta değil (YYYY-AA-GG).")
                return redirect("yeni_bakim_update", pk=pk)
            
            # İlgili kayıtları al
            try:
                arac = AracBilgileri.objects.get(id=arac_id)
            except AracBilgileri.DoesNotExist:
                messages.error(request, "Seçilen araç bulunamadı.")
                return redirect("yeni_bakim_update", pk=pk)
            
            # Diğer değerleri işle
            km_value = int(kilometre) if kilometre and str(kilometre).strip().isdigit() else None
            next_km_value = int(bir_sonraki_bakim_km) if bir_sonraki_bakim_km and str(bir_sonraki_bakim_km).strip().isdigit() else None
            
            try:
                next_date_value = datetime.strptime(bir_sonraki_bakim_tarihi, "%Y-%m-%d").date() if bir_sonraki_bakim_tarihi else None
            except ValueError:
                next_date_value = None
            
            # Bakım kaydını güncelle
            bakim.arac = arac
            bakim.bakim_turu = bakim_turu
            bakim.bakim_tarihi = bakim_tarihi_obj
            bakim.kilometre = km_value
            bakim.yapilan_islemler = yapilan_islemler
            bakim.maliyet = maliyet_float
            bakim.para_birimi = para_birimi
            bakim.kur = kur_float
            bakim.maliyet_eur = maliyet_eur
            bakim.bir_sonraki_bakim_km = next_km_value
            bakim.bir_sonraki_bakim_tarihi = next_date_value
            bakim.notlar = notlar
            bakim.save()
            
            messages.success(request, "Bakım kaydı başarıyla güncellendi.")
            return redirect("bakim_list")
        
        except Exception as e:
            import traceback
            print(f"Yeni bakım güncellenirken hata: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Bakım kaydı güncellenirken hata oluştu: {e}")
    
    # GET isteği - formu göster
    try:
        araclar = AracBilgileri.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar, para_birimleri = [], []
    
    context = {
        "bakim": bakim,
        "araclar": araclar,
        "para_birimleri": para_birimleri,
        "today": timezone.now().date()
    }
    return render(request, "sefer_app/yeni_bakim_form.html", context)

def yeni_bakim_delete(request, pk):
    try:
        bakim = get_object_or_404(YeniAracBakim, pk=pk)
        if request.method == "POST":
            bakim.delete()
            messages.success(request, "Bakım kaydı başarıyla silindi.")
            return redirect("bakim_list")
    except Exception as e:
        print(f"Bakım kaydı silinirken hata: {e}")
        bakim = None
    
    context = {
        "bakim": bakim
    }
    return render(request, "sefer_app/yeni_bakim_confirm_delete.html", context)

# Uyarı (Alert) views
def uyari_list(request):
    try:
        # Filtreleme parametreleri
        arac_id = request.GET.get('arac')
        uyari_turu = request.GET.get('uyari_turu')
        durum = request.GET.get('durum')
        oncelik = request.GET.get('oncelik')
        
        # Temel sorgu
        uyarilar = AracUyari.objects.all()
        
        # Filtreleme
        if arac_id:
            uyarilar = uyarilar.filter(arac_id=arac_id)
        if uyari_turu:
            uyarilar = uyarilar.filter(uyari_turu=uyari_turu)
        if durum:
            uyarilar = uyarilar.filter(durum=durum)
        if oncelik:
            uyarilar = uyarilar.filter(oncelik=oncelik)
        
        # Sıralama (önce acil ve geciken uyarılar)
        uyarilar = uyarilar.order_by('-oncelik', 'son_tarih', '-olusturma_tarihi')
        
        # Sayfalama
        paginator = Paginator(uyarilar, 10)  # Her sayfada 10 uyarı
        page = request.GET.get('page')
        uyarilar = paginator.get_page(page)
        
        # Tüm araç listesi (filtre için)
        araclar = AracBilgileri.objects.all()
    except Exception as e:
        print(f"Uyarılar getirilirken hata: {e}")
        uyarilar = []
        araclar = []
    
    context = {
        'uyarilar': uyarilar,
        'today': timezone.now().date(),
        'araclar': araclar,
    }
    return render(request, 'sefer_app/uyari_list.html', context)

def uyari_detay(request, pk):
    """Uyarı detaylarını gösterir"""
    try:
        uyari = get_object_or_404(AracUyari, pk=pk)
    except Exception as e:
        print(f"Uyarı detayları getirilirken hata: {e}")
        uyari = None
    
    context = {
        'uyari': uyari,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/uyari_detay.html', context)

def uyari_tamamla(request, pk):
    """Uyarıyı tamamlandı olarak işaretler"""
    try:
        uyari = get_object_or_404(AracUyari, pk=pk)
        uyari.durum = 'tamamlandi'
        # Tamamlanma tarihi model tarafında otomatik olarak atanacaktır
        uyari.save()
        messages.success(request, "Uyarı başarıyla tamamlandı olarak işaretlendi.")
    except Exception as e:
        print(f"Uyarı tamamlanırken hata: {e}")
        messages.error(request, f"Uyarı tamamlanırken hata: {str(e)}")
    
    return redirect('uyari_list')

def uyari_create(request):
    if request.method == 'POST':
        try:
            arac_id = request.POST.get('arac')
            uyari_turu = request.POST.get('uyari_turu')
            kategori = request.POST.get('kategori', '')
            uyari_mesaji = request.POST.get('uyari_mesaji')
            son_tarih = request.POST.get('son_tarih')
            durum = request.POST.get('durum', 'aktif')
            oncelik = request.POST.get('oncelik', 'orta')
            bildirim_turu = request.POST.get('bildirim_turu', 'Sistem')
            hatirlatici_gun = request.POST.get('hatirlatici_gun', 7)
            notlar = request.POST.get('notlar', '')
            
            # Veri doğrulama
            if not arac_id or not uyari_mesaji or not uyari_turu:
                messages.error(request, "Araç, uyarı türü ve mesaj alanları zorunludur.")
                # Validation failed, get vehicles for the form and re-render
                araclar = AracBilgileri.objects.all()
                context = {
                    'araclar': araclar,
                    'today': timezone.now().date(),
                }
                return render(request, 'sefer_app/uyari_form.html', context)
            
            try:
                arac = AracBilgileri.objects.get(id=arac_id)
            except AracBilgileri.DoesNotExist:
                messages.error(request, f"ID: {arac_id} olan araç bulunamadı.")
                araclar = AracBilgileri.objects.all()
                context = {
                    'araclar': araclar,
                    'today': timezone.now().date(),
                }
                return render(request, 'sefer_app/uyari_form.html', context)
            
            try:
                hatirlatici_gun = int(hatirlatici_gun)
            except ValueError:
                hatirlatici_gun = 7
            
            # Son tarih değerini doğru biçimde işleme
            parsed_son_tarih = None
            if son_tarih:
                try:
                    # Eğer tarih string olarak geliyorsa
                    parsed_son_tarih = datetime.strptime(son_tarih, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    # Geçersiz tarih biçimi, None olarak bırak
                    messages.warning(request, "Tarih biçimi geçersiz, tarih bilgisi kaydedilmedi.")
            
            # Uyarı kaydını oluştur
            uyari = AracUyari(
                arac=arac,
                uyari_turu=uyari_turu,
                kategori=kategori if kategori else None,
                uyari_mesaji=uyari_mesaji,
                son_tarih=parsed_son_tarih,
                durum=durum,
                oncelik=oncelik,
                bildirim_turu=bildirim_turu,
                hatirlatici_gun=hatirlatici_gun,
                notlar=notlar
            )
            uyari.save()
            
            messages.success(request, "Uyarı başarıyla oluşturuldu.")
            return redirect('uyari_list')
        
        except Exception as e:
            import traceback
            print(f"Uyarı oluşturulurken hata: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Uyarı oluşturulurken hata oluştu: {str(e)}")
            # Error occurred, get vehicles for the form and re-render
            try:
                araclar = AracBilgileri.objects.all()
            except Exception:
                araclar = []
            context = {
                'araclar': araclar,
                'today': timezone.now().date(),
            }
            return render(request, 'sefer_app/uyari_form.html', context)
    
    # GET isteği - yeni form gösterimi
    try:
        araclar = AracBilgileri.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar = []
    
    context = {
        'araclar': araclar,
        'today': timezone.now().date(),
    }
    return render(request, 'sefer_app/uyari_form.html', context)

def uyari_update(request, pk):
    try:
        uyari = get_object_or_404(AracUyari, pk=pk)
    except Exception as e:
        print(f"Güncellenecek uyarı bulunamadı: {e}")
        messages.error(request, f"Uyarı bulunamadı: {str(e)}")
        return redirect('uyari_list')
    
    if request.method == 'POST':
        try:
            arac_id = request.POST.get('arac')
            uyari.uyari_turu = request.POST.get('uyari_turu')
            uyari.kategori = request.POST.get('kategori', '')
            uyari.uyari_mesaji = request.POST.get('uyari_mesaji')
            son_tarih = request.POST.get('son_tarih')
            uyari.durum = request.POST.get('durum', 'aktif')
            uyari.oncelik = request.POST.get('oncelik', 'orta')
            uyari.bildirim_turu = request.POST.get('bildirim_turu', 'Sistem')
            uyari.notlar = request.POST.get('notlar', '')
            
            # Veri doğrulama
            if not arac_id or not uyari.uyari_mesaji or not uyari.uyari_turu:
                messages.error(request, "Araç, uyarı türü ve mesaj alanları zorunludur.")
                araclar = AracBilgileri.objects.all()
                context = {
                    'uyari': uyari,
                    'araclar': araclar,
                    'today': timezone.now().date(),
                }
                return render(request, 'sefer_app/uyari_form.html', context)
            
            # Son tarih değerini doğru biçimde işleme
            if son_tarih:
                try:
                    # Eğer tarih string olarak geliyorsa
                    uyari.son_tarih = datetime.strptime(son_tarih, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    # Geçersiz tarih biçimi, None olarak bırak
                    uyari.son_tarih = None
                    messages.warning(request, "Tarih biçimi geçersiz, tarih bilgisi kaydedilmedi.")
            else:
                uyari.son_tarih = None
            
            # Tamamlanma tarihi model tarafında otomatik olarak yönetilmektedir
            
            try:
                hatirlatici_gun = request.POST.get('hatirlatici_gun', 7)
                uyari.hatirlatici_gun = int(hatirlatici_gun)
            except ValueError:
                uyari.hatirlatici_gun = 7
            
            # Araç güncellemesi
            try:
                uyari.arac = AracBilgileri.objects.get(id=arac_id)
            except AracBilgileri.DoesNotExist:
                messages.error(request, f"ID: {arac_id} olan araç bulunamadı.")
                araclar = AracBilgileri.objects.all()
                context = {
                    'uyari': uyari,
                    'araclar': araclar,
                    'today': timezone.now().date(),
                }
                return render(request, 'sefer_app/uyari_form.html', context)
                
            uyari.save()
            
            messages.success(request, "Uyarı başarıyla güncellendi.")
            return redirect('uyari_list')
        
        except Exception as e:
            import traceback
            print(f"Uyarı güncellenirken hata: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Uyarı güncellenirken hata oluştu: {str(e)}")
    
    try:
        araclar = AracBilgileri.objects.all()
    except Exception as e:
        print(f"Form verileri yüklenemedi: {e}")
        araclar = []
    
    context = {
        'uyari': uyari,
        'araclar': araclar,
        'today': timezone.now().date(),
    }
    return render(request, 'sefer_app/uyari_form.html', context)

def uyari_delete(request, pk):
    try:
        uyari = get_object_or_404(AracUyari, pk=pk)
        if request.method == 'POST':
            uyari.delete()
            messages.success(request, "Uyarı başarıyla silindi.")
            return redirect('uyari_list')
    except Exception as e:
        print(f"Uyarı silinirken hata: {e}")
        uyari = None
    
    context = {
        'uyari': uyari
    }
    return render(request, 'sefer_app/uyari_confirm_delete.html', context)
