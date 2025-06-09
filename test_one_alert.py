import os
import sys
import django

# Django yapılandırması için gerekli ortam ayarları
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextsefer.settings')
django.setup()

# Django modellerini import et
from sefer_app.models import AracBilgileri, AracUyari
from django.utils import timezone
from datetime import timedelta

def test_one_alert():
    print("\n===== ARAÇ UYARI TAMAMLAMA TESTİ =====\n")
    
    # Bir araç al
    arac = AracBilgileri.objects.first()
    if not arac:
        print("Araç bulunamadı!")
        return
    
    # Test uyarısı oluştur
    uyari = AracUyari.objects.create(
        arac=arac,
        uyari_turu='vergi',
        uyari_mesaji='Test: Vergi ödeme hatırlatıcı',
        son_tarih=timezone.now().date() + timedelta(days=5),
        oncelik='orta'
    )
    
    # İlk durumu kontrol et
    print(f"Oluşturulan uyarı ID: {uyari.id}")
    print(f"Durum: {uyari.durum}")
    print(f"Tamamlanma Tarihi: {uyari.tamamlanma_tarihi}")
    
    # Durumu 'tamamlandı' olarak değiştir
    print("\nUyarı tamamlandı olarak işaretleniyor...")
    uyari.durum = 'tamamlandi'
    uyari.save()
    
    # Yeniden yükle ve tamamlanma tarihini kontrol et
    uyari.refresh_from_db()
    print(f"Yeni Durum: {uyari.durum}")
    print(f"Tamamlanma Tarihi: {uyari.tamamlanma_tarihi}")
    print(f"Bugün: {timezone.now().date()}")
    
    # Test sonucunu değerlendir
    if uyari.tamamlanma_tarihi == timezone.now().date():
        print("\n✅ TEST BAŞARILI: Tamamlanma tarihi doğru şekilde ayarlandı.")
    else:
        print("\n❌ TEST BAŞARISIZ: Tamamlanma tarihi ayarlanmadı veya yanlış tarih ayarlandı.")
    
    # Tekrar aktif yap ve tamamlanma tarihinin silinip silinmediğini kontrol et
    print("\nUyarı tekrar aktif olarak işaretleniyor...")
    uyari.durum = 'aktif'
    uyari.save()
    
    # Yeniden yükle ve tamamlanma tarihini kontrol et
    uyari.refresh_from_db()
    print(f"Yeni Durum: {uyari.durum}")
    print(f"Tamamlanma Tarihi: {uyari.tamamlanma_tarihi}")
    
    # Test sonucunu değerlendir
    if uyari.tamamlanma_tarihi is None:
        print("\n✅ TEST BAŞARILI: Durum aktife çevrildiğinde tamamlanma tarihi silindi.")
    else:
        print("\n❌ TEST BAŞARISIZ: Durum aktife çevrildiğinde tamamlanma tarihi silinmedi.")
    
    # Test verilerini temizle
    uyari.delete()
    print("\nTest uyarısı silindi.")
    
if __name__ == "__main__":
    test_one_alert() 
 
 
 
 
 
 