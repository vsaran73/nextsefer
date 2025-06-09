from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# User Profile Model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    position = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = "Kullanıcı Profil"
        verbose_name_plural = "Kullanıcı Profilleri"

# Signal to create user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

# Temel Bilgiler

class ParaBirimleri(models.Model):
    kod = models.CharField(max_length=3, unique=True)
    ad = models.CharField(max_length=50)
    sembol = models.CharField(max_length=5, blank=True, null=True)
    aktif = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.ad} ({self.kod})"
    
    class Meta:
        verbose_name = "Para Birimi"
        verbose_name_plural = "Para Birimleri"

class Ulkeler(models.Model):
    ulke_adi = models.CharField(max_length=100, unique=True)
    ulke_kodu = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.ulke_adi
    
    class Meta:
        verbose_name = "Ülke"
        verbose_name_plural = "Ülkeler"

class Sehirler(models.Model):
    ulke = models.ForeignKey(Ulkeler, on_delete=models.CASCADE, related_name='sehirler')
    sehir_adi = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.sehir_adi}, {self.ulke}"
    
    class Meta:
        verbose_name = "Şehir"
        verbose_name_plural = "Şehirler"

class FirmaBilgi(models.Model):
    unvan = models.CharField(max_length=255, verbose_name="Firma Ünvanı")
    adres = models.TextField(verbose_name="Adres", blank=True, null=True)
    telefon = models.CharField(max_length=30, verbose_name="Telefon", blank=True, null=True)
    eposta = models.EmailField(verbose_name="E-posta", blank=True, null=True)
    vergi_no = models.CharField(max_length=50, verbose_name="Vergi No", blank=True, null=True)
    vergi_dairesi = models.CharField(max_length=100, verbose_name="Vergi Dairesi", blank=True, null=True)
    web = models.URLField(verbose_name="Web Sitesi", blank=True, null=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.unvan

    class Meta:
        verbose_name = "Firma Bilgisi"
        verbose_name_plural = "Firma Bilgileri"

class Firmalar(models.Model):
    FirmaTipi = models.CharField(max_length=50)
    FirmaAdi = models.CharField(max_length=255)
    YetkiliKisi = models.CharField(max_length=150, null=True, blank=True)
    AktifMi = models.BooleanField(default=True)
    Telefon = models.CharField(max_length=20, null=True, blank=True)
    Eposta = models.EmailField(null=True, blank=True)
    WebSitesi = models.URLField(null=True, blank=True)
    Adres = models.TextField(null=True, blank=True)
    VergiNumarasi = models.CharField(max_length=20, unique=True, null=True, blank=True)
    VergiDairesi = models.CharField(max_length=100, null=True, blank=True)
    ParaBirimi = models.CharField(max_length=10)
    Notlar = models.TextField(null=True, blank=True)
    Ulke = models.ForeignKey(Ulkeler, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmalar')
    Sehir = models.ForeignKey(Sehirler, on_delete=models.SET_NULL, null=True, blank=True, related_name='firmalar')
    
    def __str__(self):
        return self.FirmaAdi
    
    class Meta:
        verbose_name = "Firma"
        verbose_name_plural = "Firmalar"

class Personeller(models.Model):
    PerAd = models.CharField(max_length=100)
    PerSoyad = models.CharField(max_length=100)
    VatandaslikNo = models.CharField(max_length=20, unique=True, null=True, blank=True)
    DogumTarihi = models.DateField(null=True, blank=True)
    Telefon = models.CharField(max_length=20, null=True, blank=True)
    Eposta = models.EmailField(unique=True, null=True, blank=True)
    Adres = models.TextField(null=True, blank=True)
    Departman = models.CharField(max_length=100)
    Pozisyon = models.CharField(max_length=100)
    Maas = models.DecimalField(max_digits=10, decimal_places=2)
    IseBaslangicTarihi = models.DateField(null=True, blank=True)
    Durum = models.CharField(max_length=50)
    Aciklama = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.PerAd} {self.PerSoyad}"
    
    class Meta:
        verbose_name = "Personel"
        verbose_name_plural = "Personeller"

class PersonelOdeme(models.Model):
    ODEME_TURLERI = (
        ('Maaş', 'Maaş'),
        ('Avans', 'Avans'),
        ('Harcırah', 'Harcırah'),
        ('Prim', 'Prim'),
        ('İkramiye', 'İkramiye'),
        ('Diğer', 'Diğer'),
    )
    
    personel = models.ForeignKey(Personeller, on_delete=models.CASCADE, related_name='odemeler')
    belge_no = models.CharField(max_length=15, unique=True)
    tarih = models.DateField()
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    odeme_turu = models.CharField(max_length=20, choices=ODEME_TURLERI)
    aciklama = models.TextField(blank=True, null=True)
    kasa = models.ForeignKey('Kasalar', on_delete=models.SET_NULL, null=True, blank=True, related_name='personel_odemeleri')
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.belge_no} - {self.personel} - {self.odeme_turu}"
    
    class Meta:
        verbose_name = "Personel Ödemesi"
        verbose_name_plural = "Personel Ödemeleri"
        ordering = ['-tarih', '-olusturulma_tarihi']

# Araç Bilgileri

class AracBilgileri(models.Model):
    plaka = models.CharField(max_length=20, unique=True)
    arac_tipi = models.CharField(max_length=50)
    kullanim_sekli = models.CharField(max_length=50)
    arac_durumu = models.CharField(max_length=50)
    marka = models.CharField(max_length=50, blank=True)
    model = models.CharField(max_length=50, blank=True)
    model_yili = models.PositiveIntegerField(null=True, blank=True)
    yakit_tipi = models.CharField(max_length=50)
    motor_no = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sasi_no = models.CharField(max_length=50, unique=True, blank=True, null=True)
    ilk_kilometre = models.PositiveIntegerField(default=0, help_text="Araç satın alındığındaki kilometre değeri")
    lastik_olculeri = models.CharField(max_length=50, blank=True)
    atanmis_sofor = models.ForeignKey(Personeller, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.plaka} - {self.marka} {self.model}"
    
    class Meta:
        verbose_name = "Araç"
        verbose_name_plural = "Araçlar"

class AracBakim(models.Model):
    arac = models.ForeignKey(AracBilgileri, on_delete=models.CASCADE, related_name='bakimlar')
    bakim_turu = models.CharField(max_length=100)
    bakim_tarihi = models.DateField()
    yapilan_islemler = models.TextField()
    maliyet = models.DecimalField(max_digits=10, decimal_places=2)
    para_birimi = models.CharField(max_length=10, default='TRY')
    kur = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    maliyet_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kasa = models.ForeignKey('Kasalar', on_delete=models.SET_NULL, null=True, blank=True, related_name='bakim_harcamalari')
    bir_sonraki_bakim_km = models.PositiveIntegerField(null=True, blank=True)
    bir_sonraki_bakim_tarihi = models.DateField(null=True, blank=True)
    notlar = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.arac.plaka} - {self.bakim_turu} ({self.bakim_tarihi})"
    
    class Meta:
        verbose_name = "Araç Bakım"
        verbose_name_plural = "Araç Bakımları"

class YeniAracBakim(models.Model):
    arac = models.ForeignKey(AracBilgileri, on_delete=models.CASCADE, related_name='yeni_bakimlar')
    bakim_turu = models.CharField(max_length=100)
    bakim_tarihi = models.DateField()
    kilometre = models.PositiveIntegerField(null=True, blank=True)
    yapilan_islemler = models.TextField(blank=True)
    maliyet = models.DecimalField(max_digits=10, decimal_places=2)
    para_birimi = models.CharField(max_length=10, default='TRY')
    kur = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    maliyet_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kasa = models.ForeignKey('Kasalar', on_delete=models.SET_NULL, null=True, blank=True, related_name='yeni_bakim_harcamalari')
    kasa_hareketi = models.ForeignKey('GenelKasaHareketi', on_delete=models.SET_NULL, null=True, blank=True, related_name='bakim_kaydi')
    belge_no = models.CharField(max_length=50, null=True, blank=True)
    bir_sonraki_bakim_km = models.PositiveIntegerField(null=True, blank=True)
    bir_sonraki_bakim_tarihi = models.DateField(null=True, blank=True)
    notlar = models.TextField(null=True, blank=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.arac.plaka} - {self.bakim_turu} ({self.bakim_tarihi})"
    
    class Meta:
        verbose_name = "Yeni Araç Bakım"
        verbose_name_plural = "Yeni Araç Bakımları"

class AracUyari(models.Model):
    ONCELIK_CHOICES = [
        ('dusuk', 'Düşük'),
        ('orta', 'Normal'),
        ('yuksek', 'Yüksek')
    ]
    
    DURUM_CHOICES = [
        ('aktif', 'Aktif'),
        ('tamamlandi', 'Tamamlandı'),
        ('ertelendi', 'Ertelendi'),
        ('iptal', 'İptal')
    ]
    
    KATEGORI_CHOICES = [
        ('muayene', 'Muayene'),
        ('sigorta', 'Sigorta'),
        ('bakim', 'Bakım'),
        ('vergi', 'Vergi'),
        ('lastik', 'Lastik Değişimi'),
        ('yag', 'Yağ Değişimi'),
        ('belge', 'Belge Yenileme'),
        ('diger', 'Diğer')
    ]
    
    arac = models.ForeignKey(AracBilgileri, on_delete=models.CASCADE, related_name='uyarilar')
    uyari_turu = models.CharField(max_length=100, choices=KATEGORI_CHOICES, default='bakim')
    kategori = models.CharField(max_length=100, null=True, blank=True)
    uyari_mesaji = models.TextField()
    olusturma_tarihi = models.DateField(auto_now_add=True)
    son_tarih = models.DateField(null=True, blank=True)
    durum = models.CharField(max_length=50, choices=DURUM_CHOICES, default="aktif")
    oncelik = models.CharField(max_length=20, choices=ONCELIK_CHOICES, default="orta")
    bildirim_turu = models.CharField(max_length=50, default="Sistem", blank=True, null=True, 
                                     help_text="Uyarı bildiriminin nasıl yapılacağını belirtir (SMS, E-posta, Sistem)")
    notlar = models.TextField(blank=True, null=True)
    hatirlatici_gun = models.PositiveIntegerField(default=7, help_text="Son tarihten kaç gün önce hatırlatma yapılacağı")
    tamamlanma_tarihi = models.DateField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Eğer durum 'tamamlandi' olarak değiştirildiyse ve tamamlanma tarihi yoksa, bugünün tarihini ata
        if self.durum == 'tamamlandi' and not self.tamamlanma_tarihi:
            self.tamamlanma_tarihi = timezone.now().date()
        # Eğer durum 'tamamlandi' değilse, tamamlanma tarihini temizle
        elif self.durum != 'tamamlandi':
            self.tamamlanma_tarihi = None
        
        super(AracUyari, self).save(*args, **kwargs)
    
    @property
    def kalan_gun(self):
        if not self.son_tarih:
            return None
        bugün = timezone.now().date()
        return (self.son_tarih - bugün).days
    
    @property
    def durum_rengi(self):
        if self.durum == 'tamamlandi':
            return 'success'
        if self.durum == 'ertelendi':
            return 'warning'
        if self.durum == 'iptal':
            return 'secondary'
        
        if not self.son_tarih:
            return 'info'
            
        kalan = self.kalan_gun
        if kalan is None:
            return 'info'
        elif kalan < 0:
            return 'danger'  # Süresi geçmiş
        elif kalan <= 3:
            return 'danger'  # Son 3 gün
        elif kalan <= 7:
            return 'warning'  # Son hafta
        else:
            return 'primary'  # Normal durum
    
    def __str__(self):
        return f"{self.arac} - {self.get_uyari_turu_display()}"
    
    class Meta:
        verbose_name = "Araç Uyarı"
        verbose_name_plural = "Araç Uyarıları"

# Finans Bilgileri

class Kasalar(models.Model):
    KASA_TIPI_CHOICES = [
        ('Nakit', 'Nakit'),
        ('Banka', 'Banka'),
        ('Kredi Kartı', 'Kredi Kartı'),
        ('Sanal POS', 'Sanal POS'),
        ('Diğer', 'Diğer')
    ]
    
    kasa_adi = models.CharField(max_length=100)
    kasa_tipi = models.CharField(max_length=50, choices=KASA_TIPI_CHOICES, default='Nakit')
    para_birimi = models.CharField(max_length=10)
    baslangic_bakiyesi = models.DecimalField(max_digits=12, decimal_places=2)
    aciklama = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.kasa_adi} ({self.para_birimi})"
    
    class Meta:
        verbose_name = "Kasa"
        verbose_name_plural = "Kasalar"

class KasaTransfer(models.Model):
    kaynak_kasa = models.ForeignKey(Kasalar, related_name='gonderilen_transferler', on_delete=models.CASCADE)
    hedef_kasa = models.ForeignKey(Kasalar, related_name='alinan_transferler', on_delete=models.CASCADE)
    tarih = models.DateField()
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    kur = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    aciklama = models.TextField(blank=True, null=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.kaynak_kasa} → {self.hedef_kasa}: {self.tutar} ({self.tarih})"
    
    class Meta:
        verbose_name = "Kasa Transferi"
        verbose_name_plural = "Kasa Transferleri"

class GenelKasaHareketi(models.Model):
    HAREKET_TIPLERI = [
        ('Gelir', 'Gelir'),
        ('Gider', 'Gider')
    ]
    
    GIDER_TURLERI = [
        ('', '-'),
        ('Sabit', 'Sabit Gider'),
        ('Değişken', 'Değişken Gider'),
        ('Beklenmeyen', 'Beklenmeyen Gider'),
        ('Operasyonel', 'Operasyonel Gider'),
        ('Yatırım', 'Yatırım'),
        ('Diğer', 'Diğer'),
    ]
    
    kasa = models.ForeignKey(Kasalar, related_name='genel_hareketler', on_delete=models.CASCADE)
    hareket_tipi = models.CharField(max_length=10, choices=HAREKET_TIPLERI)
    kategori = models.CharField(max_length=100)  # Kira, Elektrik, Ofis Gideri vs.
    gider_turu = models.CharField(max_length=20, choices=GIDER_TURLERI, blank=True, default='')  # Yeni alan
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    tarih = models.DateField()
    aciklama = models.TextField(blank=True, null=True)
    belge_no = models.CharField(max_length=50, blank=True, null=True)
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.kasa} - {self.hareket_tipi}: {self.tutar} - {self.kategori}"
    
    class Meta:
        verbose_name = "Genel Kasa Hareketi"
        verbose_name_plural = "Genel Kasa Hareketleri"

# Sefer Bilgileri

class Seferler(models.Model):
    sefer_kodu = models.CharField(max_length=50, unique=True)
    firma = models.ForeignKey(Firmalar, on_delete=models.CASCADE)
    yuk_cinsi = models.CharField(max_length=100)
    durum = models.CharField(max_length=50)
    cikis_tarihi = models.DateTimeField()
    tahmini_varis_tarihi = models.DateTimeField()
    varis_tarihi = models.DateTimeField(null=True, blank=True)  # Actual arrival date
    personel = models.ForeignKey(Personeller, on_delete=models.CASCADE)
    arac = models.ForeignKey(AracBilgileri, on_delete=models.CASCADE)
    baslangic_km = models.PositiveIntegerField(null=True, blank=True)
    bitis_km = models.PositiveIntegerField(null=True, blank=True)
    varis_kilometre = models.PositiveIntegerField(null=True, blank=True)  # Actual arrival kilometer
    toplam_kilometre = models.PositiveIntegerField(null=True, blank=True)  # Calculated total distance
    baslangic_ulkesi = models.ForeignKey(Ulkeler, on_delete=models.CASCADE, related_name='baslangic_seferleri')
    baslangic_sehri = models.ForeignKey(Sehirler, on_delete=models.CASCADE, related_name='baslangic_seferleri')
    bitis_ulkesi = models.ForeignKey(Ulkeler, on_delete=models.CASCADE, related_name='bitis_seferleri')
    bitis_sehri = models.ForeignKey(Sehirler, on_delete=models.CASCADE, related_name='bitis_seferleri')
    guzergah = models.TextField(blank=True)
    mesafe = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ucret = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notlar = models.TextField(null=True, blank=True)  # Notes field
    
    def __str__(self):
        return f"{self.sefer_kodu} - {self.baslangic_sehri} to {self.bitis_sehri}"
    
    class Meta:
        verbose_name = "Sefer"
        verbose_name_plural = "Seferler"

class SeferMasraf(models.Model):
    Sefer = models.ForeignKey(Seferler, on_delete=models.CASCADE, null=True, blank=True)
    Tarih = models.DateField()
    Tutar = models.DecimalField(max_digits=10, decimal_places=2)
    ParaBirimi = models.CharField(max_length=10)
    KurEUR = models.DecimalField(max_digits=10, decimal_places=4)
    TutarEUR = models.DecimalField(max_digits=12, decimal_places=2)
    MasrafTipi = models.CharField(max_length=50, null=True, blank=True)
    Kasa = models.ForeignKey(Kasalar, on_delete=models.CASCADE, null=True, blank=True)
    OdemeYontemi = models.CharField(max_length=50, null=True, blank=True)
    BelgeNo = models.CharField(max_length=50, null=True, blank=True)
    Aciklama = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.Sefer} - {self.Tarih} - {self.Tutar} {self.ParaBirimi}"
    
    class Meta:
        verbose_name = "Sefer Masraf"
        verbose_name_plural = "Sefer Masrafları"

# Fatura Bilgileri

class Faturalar(models.Model):
    FATURA_TIPI_CHOICES = (
        ('Alış', 'Alış'),
        ('Satış', 'Satış'),
        ('Nakliye', 'Nakliye'),
    )
    
    ODEME_DURUMU_CHOICES = (
        ('Ödenmedi', 'Ödenmedi'),
        ('Kısmi Ödeme', 'Kısmi Ödeme'),
        ('Ödendi', 'Ödendi'),
    )
    
    FaturaNo = models.CharField(max_length=50, unique=True)
    FaturaTipi = models.CharField(max_length=20, choices=FATURA_TIPI_CHOICES, default='Satış')
    Firma = models.ForeignKey(Firmalar, on_delete=models.CASCADE)
    FaturaTarihi = models.DateField()
    VadeTarihi = models.DateField(blank=True, null=True)
    ParaBirimi = models.CharField(max_length=3, default='EUR')
    AraToplam = models.DecimalField(max_digits=10, decimal_places=2)
    KDVOrani = models.DecimalField(max_digits=10, decimal_places=2)
    ToplamTutar = models.DecimalField(max_digits=10, decimal_places=2)
    OdenenTutar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    OdemeDurumu = models.CharField(max_length=20, choices=ODEME_DURUMU_CHOICES, default='Ödenmedi')
    Aciklama = models.TextField(blank=True, null=True)
    Notlar = models.TextField(blank=True, null=True)
    Sefer = models.ForeignKey(Seferler, on_delete=models.SET_NULL, null=True, blank=True, related_name="faturalar")
    OlusturmaTarihi = models.DateTimeField(default=timezone.now)
    GuncellenmeTarihi = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.FaturaNo
    
    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturalar"

class Urunler(models.Model):
    Fatura = models.ForeignKey(Faturalar, on_delete=models.CASCADE, related_name='urunler')
    Urun = models.CharField(max_length=255)
    Aciklama = models.TextField(blank=True, null=True)
    Miktar = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    Birim = models.CharField(max_length=50, default='Adet')
    BirimFiyat = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    KDV = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ToplamTutar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.Urun} - {self.Fatura.FaturaNo}"
    
    class Meta:
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

class FaturaOdeme(models.Model):
    ODEME_TIPI_CHOICES = (
        ('Nakit', 'Nakit'),
        ('Banka Transferi', 'Banka Transferi'),
        ('Kredi Kartı', 'Kredi Kartı'),
        ('Çek', 'Çek'),
        ('Senet', 'Senet'),
    )
    
    Fatura = models.ForeignKey(Faturalar, on_delete=models.CASCADE, related_name='odemeler')
    OdemeTarihi = models.DateField()
    Tutar = models.DecimalField(max_digits=10, decimal_places=2)
    OdemeTipi = models.CharField(max_length=20, choices=ODEME_TIPI_CHOICES, default='Nakit')
    Kasa = models.ForeignKey(Kasalar, on_delete=models.SET_NULL, null=True, blank=True, related_name='fatura_odemeleri')
    Aciklama = models.TextField(blank=True, null=True)
    OlusturmaTarihi = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.Fatura.FaturaNo} - {self.OdemeTarihi} - {self.Tutar}"
    
    class Meta:
        verbose_name = "Fatura Ödeme"
        verbose_name_plural = "Fatura Ödemeleri"
