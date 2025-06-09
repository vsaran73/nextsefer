from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime

from ..models import AracBilgileri, YeniAracBakim, ParaBirimleri

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

    # GET isteği — formu göster
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

