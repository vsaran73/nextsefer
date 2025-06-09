"""
Invoice (Fatura) related views.
"""

from .helpers import *
from django.db.models import Sum
from ..models import Faturalar, Firmalar, Kasalar, Urunler, FaturaOdeme, Seferler
from django.db.models import Q
from django.db import connection
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Currency symbols for formatting
CURRENCY_SYMBOLS = {
    'EUR': '€',
    'USD': '$',
    'TRY': '₺',
    'GBP': '£'
}

def format_currency(value, decimal_places=2):
    """Format a currency value with thousands separator and decimal places."""
    try:
        if value is None:
            return "0,00"
        
        # Format with European style (dot as thousand separator, comma as decimal separator)
        value_str = f"{float(value):,.{decimal_places}f}"
        # Replace decimal point with comma and thousand separator with dot
        value_str = value_str.replace(',', 'X').replace('.', ',').replace('X', '.')
        return value_str
    except Exception as e:
        print(f"Error formatting currency: {str(e)}")
        return str(value)

def generate_fatura_belge_no():
    """Generate a document number in the format FAT-MMYY-XXXX."""
    today = datetime.now()
    month_year = f"{today.month:02d}{str(today.year)[-2:]}"  # MMYY format
    prefix = f"FAT-{month_year}-"
    
    # Check for existing document numbers with this prefix
    latest_fatura = Faturalar.objects.filter(
        FaturaNo__startswith=prefix
    ).order_by('-FaturaNo').first()
    
    if latest_fatura and latest_fatura.FaturaNo and len(latest_fatura.FaturaNo) >= len(prefix) + 4:
        try:
            # Extract the numeric part and increment
            number_part = latest_fatura.FaturaNo[len(prefix):]
            number = int(number_part) + 1
        except (ValueError, IndexError):
            # If parsing fails, start from 1
            number = 1
    else:
        # No existing document, start from 1
        number = 1
    
    # Format with leading zeros to ensure 4 digits
    return f"{prefix}{number:04d}"

def fatura_list(request):
    """List all invoices with filtering options."""
    # Base queryset
    faturalar = Faturalar.objects.all().order_by('-FaturaTarihi')
    
    # Get filter parameters
    fatura_tipi = request.GET.get('fatura_tipi', '')
    durum = request.GET.get('durum', '')
    baslangic_tarihi = request.GET.get('baslangic_tarihi', '')
    bitis_tarihi = request.GET.get('bitis_tarihi', '')
    firma_id = request.GET.get('firma', '')
    arama = request.GET.get('arama', '')
    
    # Apply filters
    if fatura_tipi:
        faturalar = faturalar.filter(FaturaTipi=fatura_tipi)
        
    if durum:
        faturalar = faturalar.filter(OdemeDurumu=durum)
        
    if baslangic_tarihi:
        faturalar = faturalar.filter(FaturaTarihi__gte=baslangic_tarihi)
        
    if bitis_tarihi:
        faturalar = faturalar.filter(FaturaTarihi__lte=bitis_tarihi)
        
    if firma_id:
        faturalar = faturalar.filter(Firma_id=firma_id)
    
    if arama:
        faturalar = faturalar.filter(
            Q(FaturaNo__icontains=arama) | 
            Q(Aciklama__icontains=arama) |
            Q(Firma__FirmaAdi__icontains=arama)
        )
    
    # Check for export parameter
    export_format = request.GET.get('export', '')
    if export_format == 'pdf':
        return export_fatura_pdf(request, faturalar)
    
    # Count by status for statistics
    odenmis_fatura_sayisi = Faturalar.objects.filter(OdemeDurumu='Ödendi').count()
    kismi_odenmis_fatura_sayisi = Faturalar.objects.filter(OdemeDurumu='Kısmi Ödeme').count()
    odenmemis_fatura_sayisi = Faturalar.objects.filter(OdemeDurumu='Ödenmedi').count()
    
    # Count by invoice type and sum amounts for the invoice type summary
    alis_faturalar = Faturalar.objects.filter(FaturaTipi='Alış')
    satis_faturalar = Faturalar.objects.filter(FaturaTipi='Satış')
    nakliye_faturalar = Faturalar.objects.filter(FaturaTipi='Nakliye')
    
    alis_fatura_sayisi = alis_faturalar.count()
    satis_fatura_sayisi = satis_faturalar.count()
    nakliye_fatura_sayisi = nakliye_faturalar.count()
    
    # Sum total amounts for each type (in EUR)
    alis_fatura_toplam_eur = alis_faturalar.aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    satis_fatura_toplam_eur = satis_faturalar.aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    nakliye_fatura_toplam_eur = nakliye_faturalar.aggregate(Sum('ToplamTutar'))['ToplamTutar__sum'] or 0
    toplam_fatura_tutar_eur = alis_fatura_toplam_eur + satis_fatura_toplam_eur + nakliye_fatura_toplam_eur
    
    # Get related data for filter dropdowns
    firmalar = Firmalar.objects.filter(AktifMi=True).order_by('FirmaAdi')
    
    context = {
        'faturalar': faturalar,
        'firmalar': firmalar,
        
        # Payment status summary data
        'odenen_sayi': odenmis_fatura_sayisi,
        'kismi_odenen_sayi': kismi_odenmis_fatura_sayisi,
        'odenmemis_sayi': odenmemis_fatura_sayisi,
        'toplam_fatura_sayisi': faturalar.count(),
        
        # Invoice type summary data
        'alis_fatura_sayisi': alis_fatura_sayisi,
        'satis_fatura_sayisi': satis_fatura_sayisi,
        'nakliye_fatura_sayisi': nakliye_fatura_sayisi,
        'alis_fatura_toplam_eur': alis_fatura_toplam_eur,
        'satis_fatura_toplam_eur': satis_fatura_toplam_eur, 
        'nakliye_fatura_toplam_eur': nakliye_fatura_toplam_eur,
        'toplam_fatura_tutar_eur': toplam_fatura_tutar_eur,
        
        # Keep current filters for pagination
        'fatura_tipi_filtre': fatura_tipi,
        'durum_filtre': durum,
        'baslangic_tarihi_filtre': baslangic_tarihi,
        'bitis_tarihi_filtre': bitis_tarihi,
        'firma_filtre': firma_id,
        'arama_filtre': arama,
    }
    return render(request, 'sefer_app/fatura_list.html', context)


def fatura_detail(request, pk):
    """Display detailed information about a specific invoice."""
    fatura = get_object_or_404(Faturalar, pk=pk)
    
    # Ürünleri doğrudan SQL ile alıyoruz, ORM ile ilgili sorunları aşmak için
    urunler = []
    try:
        with connection.cursor() as cursor:
            # Invoice products
            cursor.execute(
                "SELECT * FROM sefer_app_urunler WHERE Fatura_id = %s", [pk])
            columns = [col[0] for col in cursor.description]
            raw_urunler = [dict(zip(columns, row))
                           for row in cursor.fetchall()]

            # Debug info
            print(f"SQL ile bulunan ürün sayısı: {len(raw_urunler)}")

            # Standardize field names
            for urun in raw_urunler:
                urun_dict = dict(urun)
            
                # Make sure either UrunHizmetAdi or Urun is available
                if 'UrunHizmetAdi' in urun_dict and not urun_dict.get('Urun'):
                    urun_dict['Urun'] = urun_dict['UrunHizmetAdi']
                elif 'Urun' in urun_dict and not urun_dict.get('UrunHizmetAdi'):
                    urun_dict['UrunHizmetAdi'] = urun_dict['Urun']
            
                # Make sure either KDVOrani or KDV is available
                if 'KDVOrani' in urun_dict and not urun_dict.get('KDV'):
                    urun_dict['KDV'] = urun_dict['KDVOrani']
                elif 'KDV' in urun_dict and not urun_dict.get('KDVOrani'):
                    urun_dict['KDVOrani'] = urun_dict['KDV']
                
                urunler.append(urun_dict)
    except Exception as e:
        print(f"Ürünleri alma hatası: {str(e)}")
    
    # Check if FaturaOdeme table exists
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sefer_app_faturaodeme'")
            table_exists = cursor.fetchone() is not None
        
            if table_exists:
                odemeler = FaturaOdeme.objects.filter(
                    Fatura=fatura).order_by('-OdemeTarihi')
            else:
                odemeler = []
    except Exception as e:
        print(f"Ödeme bilgisi alma hatası: {str(e)}")
        odemeler = []
    
    # Calculate payment percentage
    try:
        if fatura.ToplamTutar and fatura.ToplamTutar > 0:
            odeme_yuzdesi = int(
                (fatura.OdenenTutar / fatura.ToplamTutar) * 100)
        else:
            odeme_yuzdesi = 0
    except Exception as e:
        print(f"Ödeme yüzdesi hesaplama hatası: {str(e)}")
        odeme_yuzdesi = 0
    
    # Calculate remaining amount
    try:
        kalan_tutar = fatura.ToplamTutar - fatura.OdenenTutar
    except Exception as e:
        print(f"Kalan tutar hesaplama hatası: {str(e)}")
        kalan_tutar = 0
    
    # Get other invoices from the same company
    try:
        diger_faturalar = Faturalar.objects.filter(Firma=fatura.Firma).exclude(
            id=fatura.id).order_by('-FaturaTarihi')[:5]
    except Exception as e:
        print(f"Diğer faturaları alma hatası: {str(e)}")
        diger_faturalar = []

    # Get all cash registers for payment form
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    context = {
        'fatura': fatura,
        'urunler': urunler,
        'odemeler': odemeler,
        'odeme_yuzdesi': odeme_yuzdesi,
        'kalan_tutar': kalan_tutar,
        'diger_faturalar': diger_faturalar,
        'kasalar': kasalar,
    }
    return render(request, 'sefer_app/fatura_detail.html', context)


def fatura_create(request):
    """Create a new invoice."""
    # Get all companies and trips for select options
    firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    seferler = Seferler.objects.all().order_by('-cikis_tarihi')
    # Add cash registers for payment options
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    # Generate default invoice number in FAT-MMYY-XXXX format
    default_fatura_no = generate_fatura_belge_no()
    
    if request.method == 'POST':
        print("POST isteği alındı - fatura_create")
        print(f"Form verileri: {request.POST}")
        
        try:
            # Get form data
            fatura_tipi = request.POST.get('fatura_tipi')
            firma_id = request.POST.get('firma')
            fatura_no = request.POST.get('fatura_no')
            
            # If no invoice number provided, generate one
            if not fatura_no:
                fatura_no = generate_fatura_belge_no()
                
            print(f"Alınan form verileri: fatura_tipi={fatura_tipi}, firma_id={firma_id}, fatura_no={fatura_no}")
            
            # Kontrol et - aynı fatura numarası var mı?
            if Faturalar.objects.filter(FaturaNo=fatura_no).exists():
                messages.error(
                    request,
                    f"'{fatura_no}' numaralı fatura zaten var. Lütfen farklı bir numara girin.")
                context = {
                    'firmalar': firmalar,
                    'seferler': seferler,
                    'kasalar': kasalar,
                    'default_fatura_no': default_fatura_no,
                }
                return render(request, 'sefer_app/fatura_form.html', context)
            
            fatura_tarihi = request.POST.get('fatura_tarihi')
            vade_tarihi = request.POST.get('vade_tarihi') or None
            ilgili_sefer_id = request.POST.get('ilgili_sefer') or None
            aciklama = request.POST.get('aciklama', '')
            notlar = request.POST.get('notlar', '')
            
            ara_toplam = safe_decimal(request.POST.get('ara_toplam', '0'))
            kdv_orani = safe_decimal(request.POST.get('kdv_orani', '0'))
            genel_toplam = safe_decimal(request.POST.get('genel_toplam', '0'))
            
            # Set payment related fields to default values since the payment section was removed
            odenen_tutar = 0
            odeme_durumu = 'Ödenmedi'
            odeme_kasa_id = None
                
            # İlgili firma ve sefer nesnelerini al
            firma = Firmalar.objects.get(id=firma_id) if firma_id else None
            sefer = Seferler.objects.get(id=ilgili_sefer_id) if ilgili_sefer_id else None
                
            # 1. Adım: Fatura oluştur
            fatura = Faturalar(
                FaturaNo=fatura_no,
                FaturaTipi=fatura_tipi,
                FaturaTarihi=fatura_tarihi,
                VadeTarihi=vade_tarihi,
                Firma=firma,
                Aciklama=aciklama,
                Notlar=notlar,
                AraToplam=ara_toplam,
                KDVOrani=kdv_orani,
                ToplamTutar=genel_toplam,
                OdenenTutar=odenen_tutar,
                OdemeDurumu=odeme_durumu,
                Sefer=sefer
            )
            fatura.save()
            
            # 2. Adım: Ürünleri ekle
            urun_sayisi = int(request.POST.get('urun_sayisi', 0))
            for i in range(1, urun_sayisi + 1):
                urun_adi = request.POST.get(f'urun_{i}_adi', '')
                if not urun_adi:  # Boş ürün adı ise atla
                    continue
                
                miktar = safe_decimal(request.POST.get(f'urun_{i}_miktar', '1'))
                birim = request.POST.get(f'urun_{i}_birim', 'Adet')
                birim_fiyat = safe_decimal(request.POST.get(f'urun_{i}_fiyat', '0'))
                toplam = safe_decimal(request.POST.get(f'urun_{i}_toplam', '0'))
                kdv = safe_decimal(request.POST.get(f'urun_{i}_kdv', '0'))
                
                # Ürün kaydı oluştur
                Urunler.objects.create(
                    Fatura=fatura,
                    Urun=urun_adi,
                    Miktar=miktar,
                    Birim=birim,
                    BirimFiyat=birim_fiyat,
                    KDV=kdv,
                    ToplamTutar=toplam,
                    Aciklama=request.POST.get(f'urun_{i}_aciklama', '')
                )
            
            # 3. Adım: Ödeme kaydı ve kasa hareketi oluştur (ödeme varsa)
            if odenen_tutar > 0 and odeme_kasa_id:
                kasa = Kasalar.objects.get(id=odeme_kasa_id)
                
                # Ödeme kaydı oluştur
                FaturaOdeme.objects.create(
                    Fatura=fatura,
                    OdemeTarihi=fatura_tarihi,
                    Tutar=odenen_tutar,
                    OdemeTipi='Nakit',
                    Kasa=kasa,
                    Aciklama='Fatura oluşturulurken yapılan ödeme'
                )
                
                # Kasa hareketi oluştur
                if fatura_tipi in ['Satış', 'Nakliye']:
                    hareket_tipi = 'Gelir'
                    aciklama_prefix = 'Tahsilat'
                    islem_kategorisi = 'Fatura Tahsilatı'
                else:  # 'Alış' veya diğer tipler
                    hareket_tipi = 'Gider'
                    aciklama_prefix = 'Ödeme'
                    islem_kategorisi = 'Fatura Ödemesi'
                
                GenelKasaHareketi.objects.create(
                    kasa=kasa,
                    hareket_tipi=hareket_tipi,
                    kategori=islem_kategorisi,
                    tutar=odenen_tutar,
                    tarih=fatura_tarihi,
                    belge_no=fatura_no,
                    aciklama=f"{aciklama_prefix}: {fatura_no}"
                )
            
            # 4. Adım: Sefer ücretini güncelle (nakliye faturası ise)
            if fatura_tipi == 'Nakliye' and sefer:
                # Sefere ait tüm nakliye faturalarının toplamını hesapla
                nakliye_toplamlari = Faturalar.objects.filter(
                    Sefer=sefer, FaturaTipi='Nakliye'
                ).aggregate(toplam=Sum('ToplamTutar'))
                
                toplam_ucret = nakliye_toplamlari['toplam'] or 0
                
                # Seferin ücret bilgisini güncelle
                sefer.ucret = toplam_ucret
                sefer.save()
                
                print(f"Sefer ücreti {toplam_ucret} EUR olarak güncellendi")
            
            messages.success(request, f"{fatura_no} numaralı fatura başarıyla oluşturuldu.")
            return redirect('fatura_detail', pk=fatura.id)
            
        except Exception as e:
            messages.error(request, f"Fatura oluşturma hatası: {str(e)}")
            print(f"Hata: {str(e)}")
    
    context = {
        'firmalar': firmalar,
        'seferler': seferler,
        'kasalar': kasalar,
        'default_fatura_no': default_fatura_no,
    }
    return render(request, 'sefer_app/fatura_form.html', context)


def fatura_update(request, pk):
    """Update an existing invoice."""
    fatura = get_object_or_404(Faturalar, pk=pk)
    firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    seferler = Seferler.objects.all().order_by('-cikis_tarihi')
    kasalar = Kasalar.objects.all().order_by('kasa_adi')

    # Faturaya ait ürünleri al
    try:
        urunler = list(Urunler.objects.filter(Fatura_id=pk))
        print(f"ORM ile {len(urunler)} ürün bulundu")
    except Exception as e:
        print(f"Ürünleri alma hatası: {str(e)}")
        urunler = []

        # ORM başarısız olduysa SQL ile dene
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM sefer_app_urunler WHERE Fatura_id = %s", [pk])
                columns = [col[0] for col in cursor.description]
                urunler = []
                for row in cursor.fetchall():
                    urun_dict = dict(zip(columns, row))
                    urunler.append(urun_dict)
                print(f"SQL ile {len(urunler)} ürün bulundu")
        except Exception as e:
            print(f"SQL ile ürün alma hatası: {str(e)}")
    
    if request.method == 'POST':
        print("Fatura güncelleme POST isteği alındı")

        # Formdan gelen verileri al
        try:
            firma_id = request.POST.get('firma')
            fatura_no = request.POST.get('fatura_no')
            fatura_tipi = request.POST.get('fatura_tipi', fatura.FaturaTipi)
            fatura_tarihi = request.POST.get('fatura_tarihi')
            vade_tarihi = request.POST.get('vade_tarihi')
            ilgili_sefer_id = request.POST.get('ilgili_sefer')
            aciklama = request.POST.get('aciklama', '')
            notlar = request.POST.get('notlar', '')
        
            ara_toplam = safe_decimal(request.POST.get('ara_toplam', '0'))
            kdv_orani = safe_decimal(request.POST.get('kdv_orani', '0'))
            genel_toplam = safe_decimal(request.POST.get('genel_toplam', '0'))
            odenen_tutar = safe_decimal(request.POST.get('odenen_tutar', '0'))
            odeme_durumu = request.POST.get('odeme_durumu', 'Ödenmedi')
            odeme_kasa_id = request.POST.get('odeme_kasa')

            # Ödeme durumu ve kasa kontrolü
            if odeme_durumu in ['Ödendi', 'Kısmi Ödeme'] and odenen_tutar > 0:
                if not odeme_kasa_id and odenen_tutar > fatura.OdenenTutar:
                    messages.warning(request, 'Ödeme yapılacak kasa seçilmedi. Yeni ödeme kaydı oluşturulamayacak.')

            # Eski değerleri sakla
            eski_fatura_tipi = fatura.FaturaTipi
            eski_sefer_id = fatura.Sefer_id if hasattr(
                fatura, 'Sefer_id') else None

            print(
                f"Fatura başlık bilgileri işleniyor: {fatura_no}, {fatura_tipi}, {firma_id}, {ilgili_sefer_id}")
            print(
                f"Sayısal değerler: AraToplam={ara_toplam}, KDV={kdv_orani}, Toplam={genel_toplam}")

            # 1. Adım: Faturayı güncelle
            try:
                # Django ORM ile güncelleme yap
                fatura.Firma_id = firma_id
                fatura.FaturaNo = fatura_no
                fatura.FaturaTipi = fatura_tipi
                fatura.FaturaTarihi = fatura_tarihi
                fatura.VadeTarihi = vade_tarihi
                fatura.AraToplam = ara_toplam
                fatura.KDVOrani = kdv_orani
                fatura.ToplamTutar = genel_toplam
                
                # Ödeme kaydı ve kasa hareketi için önceki tutar sakla
                eski_odenen_tutar = fatura.OdenenTutar
                
                fatura.OdenenTutar = odenen_tutar
                fatura.OdemeDurumu = odeme_durumu
                fatura.Aciklama = aciklama
                fatura.Notlar = notlar
                fatura.Sefer_id = ilgili_sefer_id if ilgili_sefer_id else None

                fatura.save()
                print(f"Fatura #{pk} başarıyla güncellendi")
                
                # Yeni ödeme var mı? 
                if odenen_tutar > eski_odenen_tutar and odeme_kasa_id:
                    try:
                        yeni_odeme_tutari = odenen_tutar - eski_odenen_tutar
                        kasa = Kasalar.objects.get(pk=odeme_kasa_id)
                        
                        # Ödeme kaydı oluştur
                        odeme = FaturaOdeme.objects.create(
                            Fatura_id=pk,
                            OdemeTarihi=fatura_tarihi,
                            Tutar=yeni_odeme_tutari,
                            OdemeTipi='Nakit',
                            Kasa=kasa,
                            Aciklama='Güncelleme sırasında eklenen ödeme'
                        )
                        
                        # Kasa hareketi oluştur
                        if fatura_tipi in ['Satış', 'Nakliye']:
                            hareket_tipi = 'Gelir'
                            aciklama_prefix = 'Tahsilat'
                            islem_kategorisi = 'Fatura Tahsilatı'
                        else:  # 'Alış' veya diğer tipler
                            hareket_tipi = 'Gider'
                            aciklama_prefix = 'Ödeme'
                            islem_kategorisi = 'Fatura Ödemesi'
                        
                        GenelKasaHareketi.objects.create(
                            kasa=kasa,
                            hareket_tipi=hareket_tipi,
                            kategori=islem_kategorisi,
                            tutar=yeni_odeme_tutari,
                            tarih=fatura_tarihi,
                            belge_no=fatura_no,
                            aciklama=f"{aciklama_prefix}: {fatura_no} - Fatura güncelleme sırasında eklenen ödeme"
                        )
                        
                        messages.success(request, f'Yeni ödeme kaydı ({yeni_odeme_tutari} EUR) başarıyla eklendi.')
                    except Exception as e:
                        print(f"Ödeme/kasa hareketi oluşturma hatası: {str(e)}")
                        messages.warning(request, f"Fatura güncellendi ancak yeni ödeme kaydı oluşturulamadı: {str(e)}")
                
            except Exception as e:
                print(f"Fatura güncelleme hatası (ORM): {str(e)}")
                # ORM başarısız olursa SQL dene
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE sefer_app_faturalar SET
                                Firma_id = %s, FaturaNo = %s, FaturaTipi = %s,
                                FaturaTarihi = %s, VadeTarihi = %s, AraToplam = %s,
                                KDVOrani = %s, ToplamTutar = %s, OdenenTutar = %s,
                                OdemeDurumu = %s, Aciklama = %s, Notlar = %s,
                                Sefer_id = %s,
                                GuncellenmeTarihi = %s
                            WHERE id = %s
                        """,
                        [firma_id,
                         fatura_no,
                         fatura_tipi,
                         fatura_tarihi,
                         vade_tarihi,
                         ara_toplam,
                         kdv_orani,
                         genel_toplam,
                         odenen_tutar,
                         odeme_durumu,
                         aciklama,
                         notlar,
                         ilgili_sefer_id if ilgili_sefer_id else None,
                         datetime.now(),
                         pk])
                    print(f"Fatura #{pk} SQL ile güncellendi")
                except Exception as e:
                    print(f"Fatura güncelleme hatası (SQL): {str(e)}")
                    messages.error(
                        request,
                        f"Fatura güncellenirken hata oluştu: {str(e)}")
                    context = {
                        'fatura': fatura,
                        'firmalar': firmalar,
                        'seferler': seferler,
                        'kasalar': kasalar,
                        'urunler': urunler,
                    }
                    return render(
                        request, 'sefer_app/fatura_form.html', context)

            # 2. Adım: Sefer ücretlerini güncelle (nakliye faturası ise)
            # Eski sefer ve yeni sefer farklıysa her ikisinin de ücretlerini
            # güncelle
            if eski_fatura_tipi == 'Nakliye' and eski_sefer_id and eski_sefer_id != ilgili_sefer_id:
                try:
                    # Eski sefere ait nakliye faturalarının toplamını hesapla
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT SUM(ToplamTutar)
                            FROM sefer_app_faturalar
                            WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye' AND id != %s
                        """, [eski_sefer_id, pk])
                        kalan_toplam = cursor.fetchone()[0] or 0

                    # Eski seferin ücretini güncelle
                    eski_sefer = Seferler.objects.get(id=eski_sefer_id)
                    eski_sefer.ucret = kalan_toplam
                    eski_sefer.save()
                    print(
                        f"Eski sefer {eski_sefer_id} ücreti {kalan_toplam} EUR olarak güncellendi")
                except Exception as e:
                    print(f"Eski sefer ücret güncelleme hatası: {str(e)}")

            # 3. Adım: Yeni seferin ücretini güncelle (nakliye faturası ise)
            if fatura_tipi == 'Nakliye' and ilgili_sefer_id:
                try:
                    # Sefere ait nakliye faturalarının toplamını hesapla
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT SUM(ToplamTutar)
                            FROM sefer_app_faturalar
                            WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye'
                        """, [ilgili_sefer_id])
                        toplam = cursor.fetchone()[0] or 0

                    # Seferin ücretini güncelle
                    yeni_sefer = Seferler.objects.get(id=ilgili_sefer_id)
                    yeni_sefer.ucret = toplam
                    yeni_sefer.save()
                    print(
                        f"Yeni sefer {ilgili_sefer_id} ücreti {toplam} EUR olarak güncellendi")
                except Exception as e:
                    print(f"Yeni sefer ücret güncelleme hatası: {str(e)}")

            # Üründeki değişiklikleri işle - Mevcut uygulamada desteklenmiyor
            # TODO: Ürün ekleme/silme/güncelleme işlevselliği eklenecek

            messages.success(
                request, f'{fatura_no} numaralı fatura başarıyla güncellendi.')
            return redirect('fatura_detail', pk=pk)

        except Exception as e:
            messages.error(request, f"Fatura güncelleme işlemi başarısız: {str(e)}")

    context = {
        'fatura': fatura,
        'firmalar': firmalar,
        'seferler': seferler,
        'kasalar': kasalar,
        'urunler': urunler,
    }
    return render(request, 'sefer_app/fatura_form.html', context)


def odeme_ekle(request, fatura_id):
    """Add a payment to an invoice."""
    fatura = get_object_or_404(Faturalar, pk=fatura_id)
    
    if request.method == 'POST':
        try:
            odeme_tarihi = request.POST.get('odeme_tarihi')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            odeme_tipi = request.POST.get('odeme_tipi', 'Nakit')
            kasa_id = request.POST.get('kasa')
            aciklama = request.POST.get('aciklama', '')
            
            # Calculate remaining amount
            kalan_tutar = fatura.ToplamTutar - fatura.OdenenTutar
            
            if not kasa_id:
                messages.error(request, 'Kasa seçimi zorunludur.')
                return redirect('fatura_detail', pk=fatura_id)
                
            if not tutar or tutar <= 0:
                messages.error(request, 'Geçerli bir ödeme tutarı giriniz.')
                return redirect('fatura_detail', pk=fatura_id)
            
            # Prevent overpayment
            if tutar > kalan_tutar:
                messages.error(request, f'Ödeme tutarı kalan tutardan fazla olamaz. Kalan tutar: {kalan_tutar} EUR')
                return redirect('fatura_detail', pk=fatura_id)
                
            kasa = Kasalar.objects.get(id=kasa_id)
            
            # Ödeme kaydı oluştur
            odeme = FaturaOdeme.objects.create(
                Fatura=fatura,
                OdemeTarihi=odeme_tarihi,
                Tutar=tutar,
                OdemeTipi=odeme_tipi,
                Kasa=kasa,
                Aciklama=aciklama
            )
            
            # Faturanın ödenen tutarını güncelle
            fatura.OdenenTutar += tutar
            
            # Ödeme durumunu belirle
            if fatura.OdenenTutar >= fatura.ToplamTutar:
                fatura.OdemeDurumu = 'Ödendi'
            elif fatura.OdenenTutar > 0:
                fatura.OdemeDurumu = 'Kısmi Ödeme'
            else:
                fatura.OdemeDurumu = 'Ödenmedi'
                
            fatura.save()
            
            # Kasa hareketi oluştur
            if fatura.FaturaTipi in ['Satış', 'Nakliye']:
                hareket_tipi = 'Gelir'
                aciklama_prefix = 'Tahsilat'
                islem_kategorisi = 'Fatura Tahsilatı'
            else:  # 'Alış' veya diğer tipler
                hareket_tipi = 'Gider'
                aciklama_prefix = 'Ödeme'
                islem_kategorisi = 'Fatura Ödemesi'
            
            GenelKasaHareketi.objects.create(
                kasa=kasa,
                hareket_tipi=hareket_tipi,
                kategori=islem_kategorisi,
                tutar=tutar,
                tarih=odeme_tarihi,
                belge_no=fatura.FaturaNo,
                aciklama=f"{aciklama_prefix}: {fatura.FaturaNo} - {aciklama}"
            )
            
            messages.success(request, f'Ödeme kaydı başarıyla eklendi. Kalan: {fatura.ToplamTutar - fatura.OdenenTutar} EUR')
            
        except Exception as e:
            messages.error(request, f'Ödeme kaydı oluşturulurken hata: {str(e)}')
            
    return redirect('fatura_detail', pk=fatura_id)


def fatura_delete(request, pk):
    """Delete an invoice."""
    fatura = get_object_or_404(Faturalar, pk=pk)
    
    # Check for related items - collect this info for debugging
    urun_count = Urunler.objects.filter(Fatura=fatura).count()
    odeme_count = FaturaOdeme.objects.filter(Fatura=fatura).count()
    
    # Add debug info to context
    context = {
        'fatura': fatura,
        'urun_count': urun_count,
        'odeme_count': odeme_count,
        'debug_info': {}
    }
    
    if request.method == 'POST':
        try:
            # Clear related items first
            # This addresses the most common issue - related items preventing deletion
            if 'force_delete' in request.POST:
                # First try to delete related products
                try:
                    deleted_products = Urunler.objects.filter(Fatura=fatura).delete()
                    context['debug_info']['deleted_products'] = deleted_products
                    messages.success(request, f"İlişkili ürünler silindi.")
                except Exception as product_error:
                    context['debug_info']['product_error'] = str(product_error)
                    messages.error(request, f"Ürünler silinirken hata: {str(product_error)}")
                
                # Try to delete related payments
                try:
                    deleted_payments = FaturaOdeme.objects.filter(Fatura=fatura).delete()
                    context['debug_info']['deleted_payments'] = deleted_payments
                    messages.success(request, f"İlişkili ödemeler silindi.")
                except Exception as payment_error:
                    context['debug_info']['payment_error'] = str(payment_error)
                    messages.error(request, f"Ödemeler silinirken hata: {str(payment_error)}")
            
            # Check if there are still related payments
            if odeme_count > 0 and 'force_delete' not in request.POST:
                messages.error(
                    request,
                    f"Bu faturaya ait {odeme_count} ödeme kaydı bulunduğu için silinemez. "
                    f"Önce ilişkili ödemeleri silmek için 'Zorla Sil' butonunu kullanın."
                )
                context['show_force_delete'] = True
                return render(request, 'sefer_app/fatura_confirm_delete.html', context)
            
            # Check if there are related products
            if urun_count > 0 and 'force_delete' not in request.POST:
                messages.error(
                    request,
                    f"Bu faturaya ait {urun_count} ürün kaydı bulunduğu için silinemez. "
                    f"Önce ilişkili ürünleri silmek için 'Zorla Sil' butonunu kullanın."
                )
                context['show_force_delete'] = True
                return render(request, 'sefer_app/fatura_confirm_delete.html', context)
            
            # Get related trip (if any) before deletion
            sefer = fatura.Sefer
            fatura_no = fatura.FaturaNo
            fatura_tipi = fatura.FaturaTipi
            
            # Now try to delete the invoice
            try:
                fatura.delete()
                messages.success(request, f"{fatura_no} numaralı fatura başarıyla silindi.")
                
                # Update trip fee if needed
                if sefer and fatura_tipi == 'Nakliye':
                    # Calculate total from remaining invoices
                    nakliye_toplami = Faturalar.objects.filter(
                        Sefer=sefer, FaturaTipi='Nakliye'
                    ).aggregate(toplam=Sum('ToplamTutar'))['toplam'] or 0
                    
                    # Update trip
                    sefer.ucret = nakliye_toplami
                    sefer.save()
                
                # Redirect based on where deletion was initiated
                if 'next' in request.GET:
                    return redirect(request.GET.get('next'))
                else:
                    return redirect('fatura_list')
            except Exception as invoice_error:
                context['debug_info']['invoice_error'] = str(invoice_error)
                messages.error(request, f"Fatura silinirken hata: {str(invoice_error)}")
                return render(request, 'sefer_app/fatura_confirm_delete.html', context)
            
        except Exception as e:
            context['debug_info']['general_error'] = str(e)
            messages.error(request, f"Fatura silme işleminde hata: {str(e)}")
            return render(request, 'sefer_app/fatura_confirm_delete.html', context)
    
    # Add show_force_delete flag if there are related records
    if urun_count > 0 or odeme_count > 0:
        context['show_force_delete'] = True
    
    return render(request, 'sefer_app/fatura_confirm_delete.html', context)


def fatura_odeme_create(request, fatura_id):
    """Create a new payment for an invoice."""
    fatura = get_object_or_404(Faturalar, pk=fatura_id)
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    # Calculate remaining amount
    kalan_tutar = fatura.ToplamTutar - fatura.OdenenTutar
    
    if request.method == 'POST':
        try:
            # Get form data
            odeme_tarihi = request.POST.get('OdemeTarihi')
            odeme_tutari = safe_decimal(request.POST.get('Tutar', '0'))
            odeme_tipi = request.POST.get('OdemeTipi', 'Nakit')
            aciklama = request.POST.get('Aciklama', '')
            kasa_id = request.POST.get('Kasa')
            
            # Validate payment amount doesn't exceed remaining balance
            if odeme_tutari > kalan_tutar:
                messages.error(request, f'Ödeme tutarı kalan tutardan fazla olamaz. Kalan tutar: {kalan_tutar} EUR')
                context = {
                    'fatura': fatura,
                    'kasalar': kasalar,
                    'kalan_tutar': kalan_tutar,
                    'today': datetime.now(),
                }
                return render(request, 'sefer_app/odeme_form.html', context)
            
            # Create payment record
            odeme = FaturaOdeme(
                Fatura=fatura,
                OdemeTarihi=odeme_tarihi,
                Tutar=odeme_tutari,
                OdemeTipi=odeme_tipi,
                Aciklama=aciklama,
                Kasa_id=kasa_id if kasa_id else None
            )
            odeme.save()
            
            # Update invoice's paid amount and payment status
            fatura.OdenenTutar = Decimal(fatura.OdenenTutar or 0) + odeme_tutari
            
            if fatura.OdenenTutar >= fatura.ToplamTutar:
                fatura.OdemeDurumu = 'Ödendi'
            elif fatura.OdenenTutar > 0:
                fatura.OdemeDurumu = 'Kısmi Ödeme'
            else:
                fatura.OdemeDurumu = 'Ödenmedi'
                
            fatura.save()
            
            messages.success(request, 'Ödeme kaydı başarıyla oluşturuldu.')
            return redirect('fatura_detail', pk=fatura.id)
            
        except Exception as e:
            messages.error(request, f'Ödeme kaydı oluşturma hatası: {str(e)}')
    
    context = {
        'fatura': fatura,
        'kasalar': kasalar,
    }
    return render(request, 'sefer_app/odeme_form.html', context)

def export_fatura_pdf(request, faturalar_queryset=None):
    """Generate PDF report with invoice list."""
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Use provided queryset or get all invoices
    if faturalar_queryset is None:
        faturalar = Faturalar.objects.all().order_by('-FaturaTarihi')
    else:
        faturalar = faturalar_queryset
    
    # Apply filters from request
    fatura_tipi = request.GET.get('fatura_tipi', '')
    durum = request.GET.get('durum', '')
    baslangic_tarihi = request.GET.get('baslangic_tarihi', '')
    bitis_tarihi = request.GET.get('bitis_tarihi', '')
    firma_id = request.GET.get('firma', '')
    
    if fatura_tipi:
        faturalar = faturalar.filter(FaturaTipi=fatura_tipi)
    
    if durum:
        faturalar = faturalar.filter(OdemeDurumu=durum)
    
    if baslangic_tarihi:
        faturalar = faturalar.filter(FaturaTarihi__gte=baslangic_tarihi)
    
    if bitis_tarihi:
        faturalar = faturalar.filter(FaturaTarihi__lte=bitis_tarihi)
    
    if firma_id:
        faturalar = faturalar.filter(Firma_id=firma_id)
    
    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="fatura_listesi.pdf"'
    
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
    elements.append(Paragraph("Next Global Logistic", title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(turkish_safe_text("FATURA LİSTESİ"), title_style))
    
    # Add filter information if any filters are applied
    filter_info = []
    if fatura_tipi:
        filter_info.append(f"Tip: {fatura_tipi}")
    if durum:
        filter_info.append(f"Durum: {durum}")
    if baslangic_tarihi or bitis_tarihi:
        date_range = f"Tarih: {baslangic_tarihi or '...'} - {bitis_tarihi or '...'}"
        filter_info.append(date_range)
    if firma_id:
        try:
            firma = Firmalar.objects.get(id=firma_id)
            filter_info.append(f"Firma: {firma.FirmaAdi}")
        except:
            pass
    
    if filter_info:
        filter_text = turkish_safe_text("Filtreler: " + ", ".join(filter_info))
        elements.append(Paragraph(filter_text, normal_style))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Create table data
    data = [
        [
            turkish_safe_text("Fatura No"), 
            turkish_safe_text("Tip"),
            turkish_safe_text("Firma"), 
            turkish_safe_text("Tarih"), 
            turkish_safe_text("Vade"), 
            turkish_safe_text("Toplam"),
            turkish_safe_text("Ödenen"),
            turkish_safe_text("Durum")
        ]
    ]
    
    # Add invoice data rows
    for fatura in faturalar:
        # Format invoice type with appropriate label
        if fatura.FaturaTipi == "Alış":
            tip = turkish_safe_text("Alış")
        elif fatura.FaturaTipi == "Satış":
            tip = turkish_safe_text("Satış")
        else:
            tip = turkish_safe_text("Nakliye")
        
        # Format company name - sadece ilk iki kelimesini al
        firma_adi = get_first_two_words(fatura.Firma.FirmaAdi) if fatura.Firma else "-" 
        firma = turkish_safe_text(firma_adi)
        
        # Format dates
        tarih = fatura.FaturaTarihi.strftime("%d.%m.%Y") if fatura.FaturaTarihi else "-"
        vade = fatura.VadeTarihi.strftime("%d.%m.%Y") if fatura.VadeTarihi else "-"
        
        # Format amounts with currency
        para_birimi = CURRENCY_SYMBOLS.get(fatura.ParaBirimi, fatura.ParaBirimi)
        toplam = f"{format_currency(fatura.ToplamTutar)} {para_birimi}"
        odenen = f"{format_currency(fatura.OdenenTutar)} {para_birimi}"
        
        # Format payment status
        durum = turkish_safe_text(fatura.OdemeDurumu)
        
        # Add row to table data
        data.append([
            fatura.FaturaNo,
            tip,
            firma,
            tarih,
            vade,
            toplam,
            odenen,
            durum
        ])
    
    # Calculate column widths
    col_widths = [2.5*cm, 1.5*cm, 5*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm, 2*cm]
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
        ('ALIGN', (5, 1), (6, -1), 'RIGHT'),  # Right align amounts
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Add summary information
    elements.append(Spacer(1, 0.5*cm))
    
    # Calculate totals by invoice type
    alis_total = sum(f.ToplamTutar for f in faturalar if f.FaturaTipi == 'Alış')
    satis_total = sum(f.ToplamTutar for f in faturalar if f.FaturaTipi == 'Satış')
    nakliye_total = sum(f.ToplamTutar for f in faturalar if f.FaturaTipi == 'Nakliye')
    
    # Create summary table
    summary_data = [
        [turkish_safe_text("Özet Bilgiler"), ""],
        [turkish_safe_text("Toplam Fatura Sayısı:"), len(faturalar)],
        [turkish_safe_text("Alış Faturaları Toplamı:"), f"{format_currency(alis_total)} EUR"],
        [turkish_safe_text("Satış Faturaları Toplamı:"), f"{format_currency(satis_total)} EUR"],
        [turkish_safe_text("Nakliye Faturaları Toplamı:"), f"{format_currency(nakliye_total)} EUR"],
    ]
    
    summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('FONTNAME', (0, 0), (1, 0), font_bold),
        ('FONTNAME', (0, 1), (0, -1), font_name),
        ('FONTNAME', (1, 1), (1, -1), font_bold),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    
    elements.append(summary_table)
    
    # Add footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(turkish_safe_text(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), footer_style))
    elements.append(Paragraph(turkish_safe_text(f"© {datetime.now().year} NextSefer - Fatura Listesi"), footer_style))
    
    # Build PDF document
    doc.build(elements)
    
    return response

def fatura_pdf(request, fatura_id):
    """Generate a PDF for an invoice."""
    fatura = get_object_or_404(Faturalar, pk=fatura_id)
    urunler = []
    
    # Get product items using direct SQL
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM sefer_app_urunler WHERE Fatura_id = %s", [fatura_id])
            columns = [col[0] for col in cursor.description]
            raw_urunler = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            for urun in raw_urunler:
                urun_dict = dict(urun)
                if 'UrunHizmetAdi' in urun_dict and not urun_dict.get('Urun'):
                    urun_dict['Urun'] = urun_dict['UrunHizmetAdi']
                elif 'Urun' in urun_dict and not urun_dict.get('UrunHizmetAdi'):
                    urun_dict['UrunHizmetAdi'] = urun_dict['Urun']
                
                if 'KDVOrani' in urun_dict and not urun_dict.get('KDV'):
                    urun_dict['KDV'] = urun_dict['KDVOrani']
                elif 'KDV' in urun_dict and not urun_dict.get('KDVOrani'):
                    urun_dict['KDVOrani'] = urun_dict['KDV']
                
                urunler.append(urun_dict)
    except Exception as e:
        print(f"Ürünleri alma hatası: {str(e)}")
    
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Create the HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{fatura.FaturaNo}.pdf"'
    
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
    elements.append(Paragraph("Next Global Logistic", title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(turkish_safe_text(f"FATURA - {fatura.FaturaNo}"), title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Add invoice information table
    invoice_info_data = [
        [turkish_safe_text("Fatura Bilgileri"), ""],
        [turkish_safe_text("Fatura No:"), fatura.FaturaNo or "-"],
        [turkish_safe_text("Fatura Tipi:"), turkish_safe_text(fatura.FaturaTipi)],
        [turkish_safe_text("Tarih:"), fatura.FaturaTarihi.strftime("%d.%m.%Y") if fatura.FaturaTarihi else "-"],
        [turkish_safe_text("Vade Tarihi:"), fatura.VadeTarihi.strftime("%d.%m.%Y") if fatura.VadeTarihi else "-"],
        [turkish_safe_text("Firma:"), turkish_safe_text(get_first_two_words(fatura.Firma.FirmaAdi) if fatura.Firma else "-")],
        [turkish_safe_text("Vergi No:"), turkish_safe_text(fatura.Firma.VergiNumarasi if fatura.Firma else "-")],
        [turkish_safe_text("Açıklama:"), turkish_safe_text(fatura.Aciklama or "-")],
        [turkish_safe_text("Ödeme Durumu:"), turkish_safe_text(fatura.OdemeDurumu)],
    ]
    
    # Add related trip information if available
    if fatura.Sefer:
        invoice_info_data.append([
            turkish_safe_text("İlgili Sefer:"),
            turkish_safe_text(fatura.Sefer.sefer_kodu)
        ])
    
    # Create invoice information table
    invoice_info_table = Table(invoice_info_data, colWidths=[4*cm, 12*cm])
    invoice_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('SPAN', (0, 0), (1, 0)),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), font_bold),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('FONTNAME', (0, 1), (0, -1), font_bold),
        ('FONTNAME', (1, 1), (1, -1), font_name),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(invoice_info_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Products table
    elements.append(Paragraph(turkish_safe_text("Ürün/Hizmet Listesi"), subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    if urunler:
        # Create the header for products table
        products_data = [[
            turkish_safe_text("#"),
            turkish_safe_text("Ürün/Hizmet"),
            turkish_safe_text("Açıklama"),
            turkish_safe_text("Miktar"),
            turkish_safe_text("Birim"),
            turkish_safe_text("Birim Fiyat"),
            turkish_safe_text("KDV %"),
            turkish_safe_text("Toplam")
        ]]
        
        # Add rows for each product
        for i, urun in enumerate(urunler):
            products_data.append([
                str(i + 1),
                turkish_safe_text(urun.get('UrunHizmetAdi', "-")),
                turkish_safe_text(urun.get('Aciklama', "-") or "-"),
                str(urun.get('Miktar', "1")),
                urun.get('Birim', "Adet"),
                f"{format_currency(urun.get('BirimFiyat', 0))} {CURRENCY_SYMBOLS.get(fatura.ParaBirimi, fatura.ParaBirimi)}",
                str(urun.get('KDV', "0")) + "%",
                f"{format_currency(urun.get('ToplamTutar', 0))} {CURRENCY_SYMBOLS.get(fatura.ParaBirimi, fatura.ParaBirimi)}",
            ])
        
        # Create and style the products table
        col_widths = [0.8*cm, 3.7*cm, 3.5*cm, 1.5*cm, 1.5*cm, 2*cm, 1.5*cm, 2*cm]
        products_table = Table(products_data, colWidths=col_widths, repeatRows=1)
        products_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            
            # Body
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center-align item number
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Center-align quantity
            ('ALIGN', (5, 1), (7, -1), 'RIGHT'),   # Right-align prices
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(products_table)
        
        # Add totals table
        elements.append(Spacer(1, 0.3*cm))
        
        # Create totals table
        para_birimi = CURRENCY_SYMBOLS.get(fatura.ParaBirimi, fatura.ParaBirimi)
        totals_data = [
            ["", turkish_safe_text("Ara Toplam:"), f"{format_currency(fatura.AraToplam)} {para_birimi}"],
            ["", turkish_safe_text("KDV Oranı:"), f"{fatura.KDVOrani}%"],
            ["", turkish_safe_text("Genel Toplam:"), f"{format_currency(fatura.ToplamTutar)} {para_birimi}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[12*cm, 3*cm, 2*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),  # Right align amounts
            ('FONTNAME', (1, 0), (1, -1), font_bold),
            ('FONTNAME', (2, 0), (2, -1), font_bold),
            ('BACKGROUND', (1, -1), (2, -1), colors.palegreen),
            ('INNERGRID', (1, 0), (2, -1), 0.5, colors.black),
            ('BOX', (1, 0), (2, -1), 1, colors.black),
        ]))
        elements.append(totals_table)
    else:
        elements.append(Paragraph(turkish_safe_text("Faturada ürün/hizmet kaydı bulunmuyor."), normal_style))
    
    # Add notes section if there are any notes
    if fatura.Notlar:
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(turkish_safe_text("Notlar:"), subtitle_style))
        elements.append(Paragraph(turkish_safe_text(fatura.Notlar), normal_style))
    
    # Add footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(turkish_safe_text(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), footer_style))
    elements.append(Paragraph(turkish_safe_text(f"© {datetime.now().year} NextSefer - Fatura"), footer_style))
    
    # Build PDF document
    doc.build(elements)
    
    return response 