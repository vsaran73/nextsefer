import os
import sys
import django
from datetime import datetime, timedelta

# Django yapılandırması için gerekli ortam ayarları
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextsefer.settings')
django.setup()

# Django modellerini import et
from sefer_app.models import AracBilgileri, AracUyari
from django.utils import timezone

def test_alert_system():
    print("\n========== ARAÇ UYARI SİSTEMİ TEST ==========\n")
    
    # İlk aracı al
    try:
        arac = AracBilgileri.objects.first()
        if not arac:
            print("Sistemde araç bulunamadı! Önce araç ekleyin.")
            return
        print(f"Test için kullanılan araç: {arac.plaka} - {arac.marka} {arac.model}")
    except Exception as e:
        print(f"Araç verileri alınırken hata: {e}")
        return
    
    # 1. Test - Normal uyarı oluşturma
    print("\n1. Test - Normal Uyarı Oluşturma:")
    try:
        normal_uyari = AracUyari.objects.create(
            arac=arac,
            uyari_turu='muayene',
            uyari_mesaji='Test: Normal araç muayene hatırlatması',
            oncelik='orta',
            durum='aktif',
            son_tarih=timezone.now().date() + timedelta(days=15),
            hatirlatici_gun=7,
            notlar='Bu normal öncelikli bir test uyarısıdır'
        )
        print("✅ Normal uyarı başarıyla oluşturuldu.")
        print(f"  - ID: {normal_uyari.id}")
        print(f"  - Mesaj: {normal_uyari.uyari_mesaji}")
        print(f"  - Son Tarih: {normal_uyari.son_tarih}")
        print(f"  - Kalan Gün: {normal_uyari.kalan_gun}")
        print(f"  - Durum Rengi: {normal_uyari.durum_rengi}")
    except Exception as e:
        print(f"❌ Normal uyarı oluşturulurken hata: {e}")
        normal_uyari = None
    
    # 2. Test - Acil uyarı oluşturma
    print("\n2. Test - Acil Uyarı Oluşturma:")
    try:
        acil_uyari = AracUyari.objects.create(
            arac=arac,
            uyari_turu='sigorta',
            uyari_mesaji='Test: ACİL sigorta yenileme uyarısı',
            oncelik='yuksek',
            durum='aktif',
            son_tarih=timezone.now().date() + timedelta(days=2),
            hatirlatici_gun=3,
            notlar='Bu yüksek öncelikli bir test uyarısıdır'
        )
        print("✅ Acil uyarı başarıyla oluşturuldu.")
        print(f"  - ID: {acil_uyari.id}")
        print(f"  - Mesaj: {acil_uyari.uyari_mesaji}")
        print(f"  - Son Tarih: {acil_uyari.son_tarih}")
        print(f"  - Kalan Gün: {acil_uyari.kalan_gun}")
        print(f"  - Durum Rengi: {acil_uyari.durum_rengi}")
    except Exception as e:
        print(f"❌ Acil uyarı oluşturulurken hata: {e}")
    
    # 3. Test - Geçmiş tarihli uyarı oluşturma
    print("\n3. Test - Geçmiş Tarihli Uyarı Oluşturma:")
    try:
        gecmis_uyari = AracUyari.objects.create(
            arac=arac,
            uyari_turu='bakim',
            uyari_mesaji='Test: Geçmiş bakım uyarısı',
            oncelik='dusuk',
            durum='aktif',
            son_tarih=timezone.now().date() - timedelta(days=5),
            hatirlatici_gun=7,
            notlar='Bu geçmiş tarihli bir test uyarısıdır'
        )
        print("✅ Geçmiş uyarı başarıyla oluşturuldu.")
        print(f"  - ID: {gecmis_uyari.id}")
        print(f"  - Mesaj: {gecmis_uyari.uyari_mesaji}")
        print(f"  - Son Tarih: {gecmis_uyari.son_tarih}")
        print(f"  - Kalan Gün: {gecmis_uyari.kalan_gun}")
        print(f"  - Durum Rengi: {gecmis_uyari.durum_rengi}")
    except Exception as e:
        print(f"❌ Geçmiş uyarı oluşturulurken hata: {e}")
    
    # 4. Test - Tarih olmayan sürekli uyarı oluşturma
    print("\n4. Test - Sürekli Uyarı Oluşturma (Tarihsiz):")
    try:
        surekli_uyari = AracUyari.objects.create(
            arac=arac,
            uyari_turu='lastik',
            uyari_mesaji='Test: Sürekli lastik kontrol uyarısı',
            oncelik='orta',
            durum='aktif',
            son_tarih=None,
            hatirlatici_gun=7,
            notlar='Bu sürekli bir test uyarısıdır'
        )
        print("✅ Sürekli uyarı başarıyla oluşturuldu.")
        print(f"  - ID: {surekli_uyari.id}")
        print(f"  - Mesaj: {surekli_uyari.uyari_mesaji}")
        print(f"  - Son Tarih: {surekli_uyari.son_tarih}")
        print(f"  - Kalan Gün: {surekli_uyari.kalan_gun}")
        print(f"  - Durum Rengi: {surekli_uyari.durum_rengi}")
    except Exception as e:
        print(f"❌ Sürekli uyarı oluşturulurken hata: {e}")
    
    # 5. Test - Uyarı güncelleme
    print("\n5. Test - Uyarı Güncelleme:")
    if normal_uyari:
        try:
            normal_uyari.uyari_mesaji = "Test: Güncellenmiş muayene uyarısı"
            normal_uyari.oncelik = "yuksek"
            normal_uyari.durum = "tamamlandi"
            
            # Tamamlanma tarihi kontrolü
            if normal_uyari.durum == 'tamamlandi' and not normal_uyari.tamamlanma_tarihi:
                normal_uyari.tamamlanma_tarihi = timezone.now().date()
            
            normal_uyari.save()
            
            # Yeniden yükle
            normal_uyari.refresh_from_db()
            
            print("✅ Uyarı güncelleme işlemi başarılı.")
            print(f"  - Güncellenmiş Mesaj: {normal_uyari.uyari_mesaji}")
            print(f"  - Güncellenmiş Öncelik: {normal_uyari.oncelik}")
            print(f"  - Güncellenmiş Durum: {normal_uyari.durum}")
            print(f"  - Tamamlanma Tarihi: {normal_uyari.tamamlanma_tarihi}")
            print(f"  - Durum Rengi: {normal_uyari.durum_rengi}")
        except Exception as e:
            print(f"❌ Uyarı güncellenirken hata: {e}")
    else:
        print("❌ Normal uyarı oluşturulamadığı için güncelleme testi atlandı.")
    
    print("\n========== TEST TAMAMLANDI ==========")

if __name__ == "__main__":
    test_alert_system() 
 
 
 
 
 
 