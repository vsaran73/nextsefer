from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Ulkeler, Sehirler, Firmalar, Personeller, AracBilgileri, 
    AracBakim, AracUyari, Kasalar, Seferler, SeferMasraf,
    Faturalar, Urunler, FaturaOdeme, KasaTransfer, GenelKasaHareketi,
    ParaBirimleri, UserProfile, PersonelOdeme, FirmaBilgi
)

# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'get_position')
    
    def get_position(self, obj):
        try:
            return obj.profile.position
        except UserProfile.DoesNotExist:
            return "-"
    get_position.short_description = 'Position'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'phone_number')
    search_fields = ('user__username', 'user__email', 'position', 'phone_number')
    list_filter = ('position',)

class SehirlerInline(admin.TabularInline):
    model = Sehirler
    extra = 1

@admin.register(Ulkeler)
class UlkelerAdmin(admin.ModelAdmin):
    list_display = ('ulke_adi', 'ulke_kodu')
    search_fields = ('ulke_adi', 'ulke_kodu')
    inlines = [SehirlerInline]

@admin.register(Sehirler)
class SehirlerAdmin(admin.ModelAdmin):
    list_display = ('sehir_adi', 'ulke')
    list_filter = ('ulke',)
    search_fields = ('sehir_adi',)

@admin.register(Firmalar)
class FirmalarAdmin(admin.ModelAdmin):
    list_display = ('FirmaAdi', 'FirmaTipi', 'YetkiliKisi', 'Telefon', 'Eposta', 'AktifMi')
    list_filter = ('FirmaTipi', 'AktifMi')
    search_fields = ('FirmaAdi', 'YetkiliKisi', 'VergiNumarasi')
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('FirmaTipi', 'FirmaAdi', 'YetkiliKisi', 'AktifMi')
        }),
        ('İletişim Bilgileri', {
            'fields': ('Telefon', 'Eposta', 'WebSitesi', 'Adres')
        }),
        ('Vergi Bilgileri', {
            'fields': ('VergiNumarasi', 'VergiDairesi')
        }),
        ('Diğer', {
            'fields': ('ParaBirimi', 'Notlar')
        }),
    )

@admin.register(Personeller)
class PersonellerAdmin(admin.ModelAdmin):
    list_display = ('PerAd', 'PerSoyad', 'Pozisyon', 'Telefon', 'Eposta', 'Durum')
    list_filter = ('Departman', 'Pozisyon', 'Durum')
    search_fields = ('PerAd', 'PerSoyad', 'VatandaslikNo', 'Telefon', 'Eposta')
    fieldsets = (
        ('Kişisel Bilgiler', {
            'fields': ('PerAd', 'PerSoyad', 'VatandaslikNo', 'DogumTarihi')
        }),
        ('İletişim Bilgileri', {
            'fields': ('Telefon', 'Eposta', 'Adres')
        }),
        ('İş Bilgileri', {
            'fields': ('Departman', 'Pozisyon', 'Maas', 'IseBaslangicTarihi', 'Durum')
        }),
        ('Diğer', {
            'fields': ('Aciklama',)
        }),
    )

class AracBakimInline(admin.TabularInline):
    model = AracBakim
    extra = 1

class AracUyariInline(admin.TabularInline):
    model = AracUyari
    extra = 1

@admin.register(AracBilgileri)
class AracBilgileriAdmin(admin.ModelAdmin):
    list_display = ('plaka', 'marka', 'model', 'arac_tipi', 'arac_durumu', 'atanmis_sofor')
    list_filter = ('arac_tipi', 'arac_durumu', 'yakit_tipi')
    search_fields = ('plaka', 'marka', 'model', 'motor_no', 'sasi_no')
    inlines = [AracBakimInline, AracUyariInline]

@admin.register(AracBakim)
class AracBakimAdmin(admin.ModelAdmin):
    list_display = ('arac', 'bakim_turu', 'bakim_tarihi', 'maliyet', 'bir_sonraki_bakim_tarihi')
    list_filter = ('bakim_turu', 'bakim_tarihi')
    search_fields = ('arac__plaka', 'bakim_turu')

@admin.register(AracUyari)
class AracUyariAdmin(admin.ModelAdmin):
    list_display = ('arac', 'uyari_turu', 'son_tarih', 'durum', 'oncelik', 'kalan_gun')
    list_filter = ('durum', 'oncelik', 'uyari_turu')
    search_fields = ('uyari_mesaji', 'arac__plaka')
    date_hierarchy = 'son_tarih'

@admin.register(Kasalar)
class KasalarAdmin(admin.ModelAdmin):
    list_display = ('kasa_adi', 'kasa_tipi', 'para_birimi', 'baslangic_bakiyesi')
    list_filter = ('kasa_tipi', 'para_birimi')
    search_fields = ('kasa_adi',)

class SeferMasrafInline(admin.TabularInline):
    model = SeferMasraf
    extra = 1

@admin.register(Seferler)
class SeferlerAdmin(admin.ModelAdmin):
    list_display = ('sefer_kodu', 'firma', 'personel', 'arac', 'durum', 'cikis_tarihi', 'tahmini_varis_tarihi')
    list_filter = ('durum', 'cikis_tarihi', 'firma')
    search_fields = ('sefer_kodu', 'firma__FirmaAdi', 'personel__PerAd', 'arac__plaka')
    inlines = [SeferMasrafInline]
    fieldsets = (
        ('Sefer Bilgileri', {
            'fields': ('sefer_kodu', 'firma', 'yuk_cinsi', 'durum')
        }),
        ('Tarih Bilgileri', {
            'fields': ('cikis_tarihi', 'tahmini_varis_tarihi')
        }),
        ('Araç ve Personel', {
            'fields': ('personel', 'arac', 'baslangic_km', 'bitis_km')
        }),
        ('Rota Bilgileri', {
            'fields': ('baslangic_ulkesi', 'baslangic_sehri', 'bitis_ulkesi', 'bitis_sehri', 'guzergah', 'mesafe')
        }),
        ('Finansal Bilgiler', {
            'fields': ('ucret',)
        }),
    )

@admin.register(SeferMasraf)
class SeferMasrafAdmin(admin.ModelAdmin):
    list_display = ('Sefer', 'Tarih', 'Tutar', 'ParaBirimi', 'TutarEUR', 'OdemeYontemi')
    list_filter = ('Tarih', 'ParaBirimi', 'OdemeYontemi')
    search_fields = ('Sefer__sefer_kodu', 'BelgeNo', 'Aciklama')

class UrunlerInline(admin.TabularInline):
    model = Urunler
    extra = 1

class FaturaOdemeInline(admin.TabularInline):
    model = FaturaOdeme
    extra = 1

@admin.register(Faturalar)
class FaturalarAdmin(admin.ModelAdmin):
    list_display = ('FaturaNo', 'FaturaTipi', 'Firma', 'FaturaTarihi', 'ToplamTutar', 'ParaBirimi', 'OdemeDurumu')
    list_filter = ('FaturaTipi', 'FaturaTarihi', 'OdemeDurumu')
    search_fields = ('FaturaNo', 'Firma__FirmaAdi')
    inlines = [UrunlerInline, FaturaOdemeInline]
    fieldsets = (
        ('Fatura Bilgileri', {
            'fields': ('FaturaTipi', 'Firma', 'FaturaNo', 'FaturaTarihi', 'VadeTarihi', 'Sefer')
        }),
        ('Tutarlar', {
            'fields': ('AraToplam', 'KDVOrani', 'ToplamTutar', 'ParaBirimi')
        }),
        ('Ödeme Bilgileri', {
            'fields': ('OdenenTutar', 'OdemeDurumu')
        }),
        ('Diğer', {
            'fields': ('Aciklama', 'Notlar')
        }),
    )

@admin.register(Urunler)
class UrunlerAdmin(admin.ModelAdmin):
    list_display = ('Urun', 'Fatura', 'Miktar', 'Birim', 'BirimFiyat', 'KDV', 'ToplamTutar')
    list_filter = ('Fatura__FaturaTipi',)
    search_fields = ('Urun', 'Fatura__FaturaNo')

@admin.register(FaturaOdeme)
class FaturaOdemeAdmin(admin.ModelAdmin):
    list_display = ('Fatura', 'OdemeTarihi', 'Tutar', 'OdemeTipi')
    list_filter = ('OdemeTarihi', 'OdemeTipi')
    search_fields = ('Fatura__FaturaNo', 'Aciklama')

@admin.register(KasaTransfer)
class KasaTransferAdmin(admin.ModelAdmin):
    list_display = ('kaynak_kasa', 'hedef_kasa', 'tarih', 'tutar', 'olusturma_tarihi')
    list_filter = ('tarih', 'kaynak_kasa', 'hedef_kasa')
    search_fields = ('aciklama', 'kaynak_kasa__kasa_adi', 'hedef_kasa__kasa_adi')
    date_hierarchy = 'tarih'

@admin.register(GenelKasaHareketi)
class GenelKasaHareketiAdmin(admin.ModelAdmin):
    list_display = ('kasa', 'hareket_tipi', 'kategori', 'gider_turu', 'tarih', 'tutar', 'belge_no')
    list_filter = ('hareket_tipi', 'kategori', 'gider_turu', 'tarih', 'kasa')
    search_fields = ('aciklama', 'belge_no', 'kategori', 'kasa__kasa_adi')
    date_hierarchy = 'tarih'

@admin.register(ParaBirimleri)
class ParaBirimleriAdmin(admin.ModelAdmin):
    list_display = ('kod', 'ad', 'sembol', 'aktif')
    search_fields = ('kod', 'ad')
    list_filter = ('aktif',)

@admin.register(PersonelOdeme)
class PersonelOdemeAdmin(admin.ModelAdmin):
    list_display = ('belge_no', 'personel', 'tarih', 'tutar', 'odeme_turu')
    list_filter = ('odeme_turu', 'tarih')
    search_fields = ('belge_no', 'personel__PerAd', 'personel__PerSoyad')
    date_hierarchy = 'tarih'
    raw_id_fields = ('personel',)

@admin.register(FirmaBilgi)
class FirmaBilgiAdmin(admin.ModelAdmin):
    list_display = ("unvan", "telefon", "eposta", "vergi_no", "vergi_dairesi", "web")
    search_fields = ("unvan", "telefon", "eposta", "vergi_no", "vergi_dairesi")
