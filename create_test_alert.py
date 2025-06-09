import os
import sys
import django

# Django yapılandırması için gerekli ortam ayarları
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextsefer.settings')
django.setup()

# Django modellerini import et
from sefer_app.models import AracBilgileri, AracUyari
from django.utils import timezone

def create_test_alert():
    # İlk aracı al
    arac = AracBilgileri.objects.first()
    
    if not arac:
        print("Sistemde araç bulunamadı! Önce araç ekleyin.")
        return
    
    # Test uyarısı oluştur
    uyari = AracUyari.objects.create(
        arac=arac,
        uyari_turu='muayene',  # muayene, sigorta, bakim, vergi, lastik, yag, belge, diger
        uyari_mesaji='Test: Araç muayene tarihi yaklaşıyor',
        oncelik='yuksek',  # dusuk, orta, yuksek
        durum='aktif',  # aktif, tamamlandi, ertelendi, iptal
        son_tarih=timezone.now().date() + timezone.timedelta(days=10),
        hatirlatici_gun=5,
        notlar='Bu bir test uyarısıdır'
    )
    
    print(f"Test uyarısı oluşturuldu! ID: {uyari.id}")
    print(f"Uyarı Türü: {uyari.get_uyari_turu_display()}")
    print(f"Son Tarih: {uyari.son_tarih}")
    print(f"Öncelik: {uyari.get_oncelik_display()}")

if __name__ == "__main__":
    create_test_alert() 