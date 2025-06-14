from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import datetime
from ..models import AracBilgileri, AracBakim, YeniAracBakim, AracUyari, GenelKasaHareketi, Kasalar, ParaBirimleri, Personeller

def generate_document_number():
    """Generate a document number in the format BKM-YYYYMM-X"""
    today = datetime.datetime.now()
    year_month = f"{today.year}{today.month:02d}"
    prefix = f"BKM-{year_month}-"
    
    # Check for existing document numbers and increment
    try:
        latest_bakim = YeniAracBakim.objects.filter(belge_no__startswith=prefix).order_by('-belge_no').first()
        if latest_bakim and latest_bakim.belge_no:
            # Extract the number part and increment
            last_num = int(latest_bakim.belge_no.split('-')[-1])
            return f"{prefix}{last_num + 1}"
    except:
        pass
    
    # If no existing number or error, start with 1
    return f"{prefix}1"

# Araç (Vehicle) views
def arac_list(request):
    # Debug: Print info to server console
    print("=== ARAC LIST DEBUG ===")
    try:
        araclar = AracBilgileri.objects.all()
        print(f"Found {araclar.count()} vehicles in database")
        for arac in araclar:
            print(f"Araç: {arac}")
    except Exception as e:
        print(f"Error retrieving vehicles: {e}")
        araclar = []
    
    context = {
        'araclar': araclar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/arac_list.html', context)

def arac_detail(request, pk):
    try:
        arac = get_object_or_404(AracBilgileri, pk=pk)
        bakimlar = AracBakim.objects.filter(arac=arac)
        uyarilar = AracUyari.objects.filter(arac=arac)
    except Exception as e:
        print(f"Error retrieving vehicle details: {e}")
        arac = None
        bakimlar = []
        uyarilar = []
    
    context = {
        'arac': arac,
        'bakimlar': bakimlar,
        'uyarilar': uyarilar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/arac_detail.html', context)

def arac_create(request):
    if request.method == 'POST':
        # Process form data
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
            kilometre = request.POST.get('kilometre')
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
                kilometre=kilometre if kilometre else 0,
                lastik_olculeri=lastik_olculeri,
                atanmis_sofor=atanmis_sofor
            )
            arac.save()
            
            messages.success(request, "Araç başarıyla kaydedildi.")
            return redirect('arac_list')
        
        except Exception as e:
            print(f"Error creating vehicle: {e}")
            messages.error(request, f"Araç kaydedilirken hata oluştu: {e}")
    
    try:
        personeller = Personeller.objects.all()
    except Exception as e:
        print(f"Error preparing form context: {e}")
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
        print(f"Error retrieving vehicle for update: {e}")
        arac = None
        return redirect('arac_list')
    
    if request.method == 'POST':
        # Process form data
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
            arac.kilometre = request.POST.get('kilometre') or 0
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
            print(f"Error updating vehicle: {e}")
            messages.error(request, f"Araç güncellenirken hata oluştu: {e}")
    
    try:
        personeller = Personeller.objects.all()
    except Exception as e:
        print(f"Error preparing form context: {e}")
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
        print(f"Error deleting vehicle: {e}")
        arac = None
    
    context = {
        'arac': arac
    }
    return render(request, 'sefer_app/arac_confirm_delete.html', context)

# Bakım (Maintenance) views
def bakim_list(request):
    try:
        bakimlar = AracBakim.objects.all().order_by('-bakim_tarihi')
    except Exception as e:
        print(f"Error retrieving maintenance records: {e}")
        bakimlar = []
    
    context = {
        'bakimlar': bakimlar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/bakim_list.html', context)

def bakim_create(request):
    if request.method == 'POST':
        # Get form data
        try:
            arac_id = request.POST.get('arac')
            bakim_turu = request.POST.get('bakim_turu')
            bakim_tarihi = request.POST.get('bakim_tarihi')
            yapilan_islemler = request.POST.get('yapilan_islemler')
            maliyet = request.POST.get('maliyet')
            para_birimi = request.POST.get('para_birimi')
            kasa_id = request.POST.get('kasa')
            
            # Get additional fields
            bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km')
            bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi')
            notlar = request.POST.get('notlar')
            
            # Get exchange rate
            kur = request.POST.get('kur', '1.0')
            if not kur:
                kur = '1.0'
            
            # Calculate EUR amount if needed
            maliyet_eur = None
            if para_birimi != 'EUR':
                maliyet_eur = float(maliyet) / float(kur)
            else:
                maliyet_eur = float(maliyet)
            
            # Create maintenance record
            arac = AracBilgileri.objects.get(id=arac_id)
            kasa = None
            if kasa_id:
                kasa = Kasalar.objects.get(id=kasa_id)
            
            belge_no = generate_document_number()
            
            bakim = AracBakim(
                arac=arac,
                bakim_turu=bakim_turu,
                bakim_tarihi=bakim_tarihi,
                yapilan_islemler=yapilan_islemler,
                maliyet=maliyet,
                para_birimi=para_birimi,
                kur=kur,
                maliyet_eur=maliyet_eur,
                kasa=kasa,
                bir_sonraki_bakim_km=bir_sonraki_bakim_km if bir_sonraki_bakim_km else None,
                bir_sonraki_bakim_tarihi=bir_sonraki_bakim_tarihi if bir_sonraki_bakim_tarihi else None,
                notlar=notlar
            )
            bakim.save()
            
            messages.success(request, "Bakım kaydı başarıyla oluşturuldu.")
            return redirect('bakim_list')
        
        except Exception as e:
            print(f"Error creating maintenance record: {e}")
            messages.error(request, f"Bakım kaydı oluşturulurken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
    except Exception as e:
        print(f"Error preparing form context: {e}")
        araclar = []
        kasalar = []
        para_birimleri = []
    
    context = {
        'araclar': araclar,
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/bakim_form.html', context)

def bakim_update(request, pk):
    try:
        bakim = get_object_or_404(AracBakim, pk=pk)
    except Exception as e:
        print(f"Error retrieving maintenance record: {e}")
        bakim = None
        return redirect('bakim_list')
    
    if request.method == 'POST':
        # Process form data
        try:
            bakim.arac_id = request.POST.get('arac')
            bakim.bakim_turu = request.POST.get('bakim_turu')
            bakim.bakim_tarihi = request.POST.get('bakim_tarihi')
            bakim.yapilan_islemler = request.POST.get('yapilan_islemler')
            bakim.maliyet = request.POST.get('maliyet')
            bakim.para_birimi = request.POST.get('para_birimi')
            
            # Get additional fields
            bakim.bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km')
            bakim.bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi')
            bakim.notlar = request.POST.get('notlar')
            
            # Get exchange rate
            kur = request.POST.get('kur', '1.0')
            if not kur:
                kur = '1.0'
            bakim.kur = kur
            
            # Calculate EUR amount if needed
            if bakim.para_birimi != 'EUR':
                bakim.maliyet_eur = float(bakim.maliyet) / float(kur)
            else:
                bakim.maliyet_eur = float(bakim.maliyet)
            
            kasa_id = request.POST.get('kasa')
            if kasa_id:
                bakim.kasa = Kasalar.objects.get(id=kasa_id)
            else:
                bakim.kasa = None
            
            bakim.save()
            
            messages.success(request, "Bakım kaydı başarıyla güncellendi.")
            return redirect('bakim_list')
        
        except Exception as e:
            print(f"Error updating maintenance record: {e}")
            messages.error(request, f"Bakım kaydı güncellenirken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
    except Exception as e:
        print(f"Error preparing form context: {e}")
        araclar = []
        kasalar = []
        para_birimleri = []
    
    context = {
        'bakim': bakim,
        'araclar': araclar,
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
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
        print(f"Error deleting maintenance record: {e}")
        bakim = None
    
    context = {
        'bakim': bakim
    }
    return render(request, 'sefer_app/bakim_confirm_delete.html', context)

# Yeni Bakım (New Maintenance) views
def yeni_bakim_list(request):
    try:
        bakimlar = YeniAracBakim.objects.all().order_by('-bakim_tarihi')
    except Exception as e:
        print(f"Error retrieving new maintenance records: {e}")
        bakimlar = []
    
    context = {
        'bakimlar': bakimlar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/yeni_bakim_list.html', context)

def yeni_bakim_create(request):
    if request.method == 'POST':
        try:
            # Debug logging
            print("=== FORM SUBMISSION DEBUG ===")
            print(f"POST data: {request.POST}")
            
            # Get form data
            arac_id = request.POST.get('arac')
            bakim_turu = request.POST.get('bakim_turu')
            bakim_tarihi = request.POST.get('bakim_tarihi')
            km = request.POST.get('km')  # Form field is named 'km'
            yapilan_islemler = request.POST.get('yapilan_islemler')
            maliyet = request.POST.get('maliyet')
            para_birimi = request.POST.get('para_birimi')
            kasa_id = request.POST.get('kasa')
            bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km')
            bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi')
            notlar = request.POST.get('notlar')
            
            # Parse exchange rate
            kur = request.POST.get('kur', '1.0')
            if not kur or kur.strip() == '':
                kur = '1.0'
            
            # Calculate EUR amount
            if para_birimi == 'EUR':
                maliyet_eur = float(maliyet)
            else:
                maliyet_eur = float(maliyet) / float(kur)
            
            # Get related objects
            arac = AracBilgileri.objects.get(id=arac_id)
            kasa = None
            if kasa_id:
                kasa = Kasalar.objects.get(id=kasa_id)
            
            # Generate document number
            belge_no = generate_document_number()
            
            # Create cash transaction
            kasa_hareketi = None
            if kasa:
                kasa_hareketi = GenelKasaHareketi(
                    kasa=kasa,
                    hareket_tipi='Gider',
                    kategori='Araç Bakım',
                    tutar=maliyet,
                    tarih=bakim_tarihi,
                    aciklama=f"{arac.plaka} - {bakim_turu}",
                    belge_no=belge_no
                )
                kasa_hareketi.save()
                print(f"Kasa hareketi oluşturuldu: ID={kasa_hareketi.id}")
            
            # Process kilometer values
            km_value = None
            if km and str(km).strip():
                km_value = int(km)
            
            next_km_value = None
            if bir_sonraki_bakim_km and str(bir_sonraki_bakim_km).strip():
                next_km_value = int(bir_sonraki_bakim_km)
            
            # Create maintenance record
            bakim = YeniAracBakim(
                arac=arac,
                bakim_turu=bakim_turu,
                bakim_tarihi=bakim_tarihi,
                kilometre=km_value,
                yapilan_islemler=yapilan_islemler,
                maliyet=maliyet,
                para_birimi=para_birimi,
                kur=kur,
                maliyet_eur=maliyet_eur,
                kasa=kasa,
                kasa_hareketi=kasa_hareketi,
                belge_no=belge_no,
                bir_sonraki_bakim_km=next_km_value,
                bir_sonraki_bakim_tarihi=bir_sonraki_bakim_tarihi if bir_sonraki_bakim_tarihi else None,
                notlar=notlar
            )
            bakim.save()
            print(f"Yeni bakım kaydı oluşturuldu: ID={bakim.id}")
            
            messages.success(request, "Yeni bakım kaydı başarıyla oluşturuldu.")
            return redirect('bakim_list')
            
        except Exception as e:
            import traceback
            print(f"HATA: {e}")
            print(traceback.format_exc())
            messages.error(request, f"Bakım kaydı oluşturulurken hata oluştu: {e}")
    
    # Form context for GET request
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
        
        # Print debug info
        print(f"Araçlar: {araclar.count()}")
        print(f"Kasalar: {kasalar.count()}")
        print(f"Para Birimleri: {para_birimleri.count()}")
        
    except Exception as e:
        print(f"Form context error: {e}")
        araclar = []
        kasalar = []
        para_birimleri = []
    
    context = {
        'araclar': araclar,
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date(),
        'belge_no': generate_document_number()
    }
    return render(request, 'sefer_app/yeni_bakim_form.html', context)

def yeni_bakim_update(request, pk):
    try:
        yeni_bakim = get_object_or_404(YeniAracBakim, pk=pk)
    except Exception as e:
        print(f"Error retrieving new maintenance record: {e}")
        yeni_bakim = None
        return redirect('yeni_bakim_list')
    
    if request.method == 'POST':
        # Process form data similar to bakim_update
        try:
            yeni_bakim.arac_id = request.POST.get('arac')
            yeni_bakim.bakim_turu = request.POST.get('bakim_turu')
            yeni_bakim.bakim_tarihi = request.POST.get('bakim_tarihi')
            
            km = request.POST.get('km')  # Form field is named 'km'
            if km and str(km).strip():
                yeni_bakim.kilometre = int(km)
            else:
                yeni_bakim.kilometre = None
                
            yeni_bakim.yapilan_islemler = request.POST.get('yapilan_islemler')
            yeni_bakim.maliyet = request.POST.get('maliyet')
            yeni_bakim.para_birimi = request.POST.get('para_birimi')
            
            # Get additional fields
            bir_sonraki_bakim_km = request.POST.get('bir_sonraki_bakim_km')
            if bir_sonraki_bakim_km and str(bir_sonraki_bakim_km).strip():
                yeni_bakim.bir_sonraki_bakim_km = int(bir_sonraki_bakim_km)
            else:
                yeni_bakim.bir_sonraki_bakim_km = None
                
            yeni_bakim.bir_sonraki_bakim_tarihi = request.POST.get('bir_sonraki_bakim_tarihi')
            yeni_bakim.notlar = request.POST.get('notlar')
            
            # Get exchange rate
            kur = request.POST.get('kur', '1.0')
            if not kur or kur.strip() == '':
                kur = '1.0'
            yeni_bakim.kur = kur
            
            # Calculate EUR amount if needed
            if yeni_bakim.para_birimi != 'EUR':
                yeni_bakim.maliyet_eur = float(yeni_bakim.maliyet) / float(kur)
            else:
                yeni_bakim.maliyet_eur = float(yeni_bakim.maliyet)
            
            kasa_id = request.POST.get('kasa')
            if kasa_id:
                yeni_bakim.kasa = Kasalar.objects.get(id=kasa_id)
            else:
                yeni_bakim.kasa = None
            
            yeni_bakim.save()
            
            messages.success(request, "Yeni bakım kaydı başarıyla güncellendi.")
            return redirect('bakim_list')
        
        except Exception as e:
            print(f"Error updating new maintenance record: {e}")
            messages.error(request, f"Yeni bakım kaydı güncellenirken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
        kasalar = Kasalar.objects.all()
        para_birimleri = ParaBirimleri.objects.filter(aktif=True)
    except Exception as e:
        print(f"Error preparing form context: {e}")
        araclar = []
        kasalar = []
        para_birimleri = []
    
    context = {
        'bakim': yeni_bakim,  # Use 'bakim' to match template variable
        'araclar': araclar,
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/yeni_bakim_form.html', context)

def yeni_bakim_delete(request, pk):
    try:
        yeni_bakim = get_object_or_404(YeniAracBakim, pk=pk)
        if request.method == 'POST':
            # Delete associated cash transaction if exists
            if yeni_bakim.kasa_hareketi:
                yeni_bakim.kasa_hareketi.delete()
            
            yeni_bakim.delete()
            messages.success(request, "Yeni bakım kaydı başarıyla silindi.")
            return redirect('bakim_list')
    except Exception as e:
        print(f"Error deleting new maintenance record: {e}")
        yeni_bakim = None
    
    context = {
        'bakim': yeni_bakim  # Use 'bakim' to match template variable
    }
    return render(request, 'sefer_app/yeni_bakim_confirm_delete.html', context)

# Uyarı (Alert) views
def uyari_list(request):
    try:
        uyarilar = AracUyari.objects.all().order_by('-olusturma_tarihi')
    except Exception as e:
        print(f"Error retrieving alerts: {e}")
        uyarilar = []
    
    context = {
        'uyarilar': uyarilar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/uyari_list.html', context)

def uyari_create(request):
    if request.method == 'POST':
        try:
            arac_id = request.POST.get('arac')
            uyari_turu = request.POST.get('uyari_turu')
            uyari_mesaji = request.POST.get('uyari_mesaji')
            son_tarih = request.POST.get('son_tarih')
            durum = request.POST.get('durum', 'Aktif')
            
            arac = AracBilgileri.objects.get(id=arac_id)
            
            uyari = AracUyari(
                arac=arac,
                uyari_turu=uyari_turu,
                uyari_mesaji=uyari_mesaji,
                son_tarih=son_tarih if son_tarih else None,
                durum=durum
            )
            uyari.save()
            
            messages.success(request, "Uyarı başarıyla oluşturuldu.")
            return redirect('uyari_list')
        
        except Exception as e:
            print(f"Error creating alert: {e}")
            messages.error(request, f"Uyarı oluşturulurken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
    except Exception as e:
        print(f"Error preparing form context: {e}")
        araclar = []
    
    context = {
        'araclar': araclar,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/uyari_form.html', context)

def uyari_update(request, pk):
    try:
        uyari = get_object_or_404(AracUyari, pk=pk)
    except Exception as e:
        print(f"Error retrieving alert: {e}")
        uyari = None
        return redirect('uyari_list')
    
    if request.method == 'POST':
        try:
            uyari.arac_id = request.POST.get('arac')
            uyari.uyari_turu = request.POST.get('uyari_turu')
            uyari.uyari_mesaji = request.POST.get('uyari_mesaji')
            uyari.son_tarih = request.POST.get('son_tarih')
            uyari.durum = request.POST.get('durum', 'Aktif')
            
            uyari.save()
            
            messages.success(request, "Uyarı başarıyla güncellendi.")
            return redirect('uyari_list')
        
        except Exception as e:
            print(f"Error updating alert: {e}")
            messages.error(request, f"Uyarı güncellenirken hata oluştu: {e}")
    
    try:
        araclar = AracBilgileri.objects.all()
    except Exception as e:
        print(f"Error preparing form context: {e}")
        araclar = []
    
    context = {
        'uyari': uyari,
        'araclar': araclar,
        'today': timezone.now().date()
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
        print(f"Error deleting alert: {e}")
        uyari = None
    
    context = {
        'uyari': uyari
    }
    return render(request, 'sefer_app/uyari_confirm_delete.html', context)