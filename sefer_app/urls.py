from django.urls import path
from .views.index_views import index, firma_bilgi_kurulum
from .views.firma_views import firma_list, firma_create, firma_update, firma_delete, firma_detail, firma_print, firma_pdf
from .views.sefer_views import (
    sefer_list, sefer_create, sefer_update, sefer_delete, sefer_detail,
    sefer_masraf_create, sefer_masraf_pdf, sefer_update_status, sefer_detail_pdf,
    sefer_masraf_analiz_pdf
)
from .views.personel_views import (
    personel_list, personel_create, personel_update, personel_delete, personel_detail,
    personel_odeme_create, personel_odeme_update, personel_odeme_delete,
    export_personel_pdf, export_personel_excel, personel_detail_pdf
)
from .views.fatura_views import (
    fatura_list, fatura_create, fatura_update, fatura_delete, fatura_detail,
    fatura_odeme_create, odeme_ekle, fatura_pdf
)
from .views import arac_views
from .views.arac_views import generate_document_number
from .views.kasa_views import (
    kasa_list, kasa_detail, kasa_create, kasa_update, kasa_delete, 
    kasa_transfer_create, genel_hareket_create, genel_hareket_update, genel_hareket_delete,
    kasa_detail_pdf, get_live_exchange_rate_ajax
)
from .views.masraf_views import masraf_list, masraf_create, masraf_update, masraf_delete, masraf_sil
from .views.helpers import get_cities_by_country
from .views.profile_views import profile_view, admin_to_profile_redirect
from .views.backup_views import backup_view
from .views.auth_views import login_view, logout_view, auto_login, check_admin_user, register_admin_view

urlpatterns = [
    # Auth URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('auto-login/', auto_login, name='auto_login'),
    
    # Dashboard
    path('', index, name='index'),
    
    # User Profile
    path('profile/', profile_view, name='profile'),
    path('admin-to-profile/', admin_to_profile_redirect, name='admin_to_profile'),
    
    # Firmalar (Companies)
    path('firmalar/', firma_list, name='firma_list'),
    path('firmalar/yeni/', firma_create, name='firma_create'),
    path('firmalar/<int:pk>/', firma_detail, name='firma_detail'),
    path('firmalar/<int:pk>/duzenle/', firma_update, name='firma_update'),
    path('firmalar/<int:pk>/sil/', firma_delete, name='firma_delete'),
    path('firmalar/<int:pk>/yazdir/', firma_print, name='firma_print'),
    path('firmalar/<int:pk>/pdf/', firma_pdf, name='firma_pdf'),
    
    # Seferler (Trips)
    path('seferler/', sefer_list, name='sefer_list'),
    path('seferler/yeni/', sefer_create, name='sefer_create'),
    path('seferler/<int:pk>/', sefer_detail, name='sefer_detail'),
    path('seferler/<int:pk>/pdf/', sefer_detail_pdf, name='sefer_detail_pdf'),
    path('seferler/<int:pk>/masraf-analiz-pdf/', sefer_masraf_analiz_pdf, name='sefer_masraf_analiz_pdf'),
    path('seferler/<int:pk>/duzenle/', sefer_update, name='sefer_update'),
    path('seferler/<int:pk>/sil/', sefer_delete, name='sefer_delete'),
    path('seferler/<int:pk>/durum-guncelle/', sefer_update_status, name='sefer_update_status'),
    path('seferler/<int:sefer_id>/masraf/yeni/', sefer_masraf_create, name='sefer_masraf_create'),
    path('seferler/<int:sefer_id>/masraf/pdf/', sefer_masraf_pdf, name='sefer_masraf_pdf'),
    
    # Personeller (Personnel)
    path('personeller/', personel_list, name='personel_list'),
    path('personeller/yeni/', personel_create, name='personel_create'),
    path('personeller/<int:pk>/', personel_detail, name='personel_detail'),
    path('personeller/<int:pk>/pdf/', personel_detail_pdf, name='personel_detail_pdf'),
    path('personeller/<int:pk>/duzenle/', personel_update, name='personel_update'),
    path('personeller/<int:pk>/sil/', personel_delete, name='personel_delete'),
    
    # Personel Ödemeleri
    path('personeller/<int:personel_pk>/odeme/', personel_odeme_create, name='personel_odeme_create'),
    path('personeller/odeme/<int:pk>/duzenle/', personel_odeme_update, name='personel_odeme_update'),
    path('personeller/odeme/<int:pk>/sil/', personel_odeme_delete, name='personel_odeme_delete'),
    
    # Faturalar (Invoices)
    path('faturalar/', fatura_list, name='fatura_list'),
    path('faturalar/yeni/', fatura_create, name='fatura_create'),
    path('faturalar/<int:pk>/', fatura_detail, name='fatura_detail'),
    path('faturalar/<int:pk>/duzenle/', fatura_update, name='fatura_update'),
    path('faturalar/<int:pk>/sil/', fatura_delete, name='fatura_delete'),
    path('faturalar/<int:fatura_id>/odeme/yeni/', fatura_odeme_create, name='fatura_odeme_create'),
    path('faturalar/<int:fatura_id>/odeme-ekle/', odeme_ekle, name='odeme_ekle'),
    path('faturalar/<int:fatura_id>/pdf/', fatura_pdf, name='fatura_pdf'),
    
    # Araçlar (Vehicles)
    path('araclar/', arac_views.arac_list, name='arac_list'),
    path('araclar/<int:pk>/', arac_views.arac_detail, name='arac_detail'),
    path('araclar/<int:pk>/pdf/', arac_views.arac_detail_pdf, name='arac_detail_pdf'),
    path('araclar/ekle/', arac_views.arac_create, name='arac_create'),
    path('araclar/<int:pk>/duzenle/', arac_views.arac_update, name='arac_update'),
    path('araclar/<int:pk>/sil/', arac_views.arac_delete, name='arac_delete'),
    
    # Bakımlar (Maintenance)
    path('bakimlar/', arac_views.bakim_list, name='bakim_list'),
    path('bakimlar/ekle/', arac_views.bakim_create, name='bakim_create'),
    path('bakimlar/<int:pk>/duzenle/', arac_views.bakim_update, name='bakim_update'),
    path('bakimlar/<int:pk>/sil/', arac_views.bakim_delete, name='bakim_delete'),
    
    # Yeni Bakım URL'leri
    path('yeni-bakimlar/', arac_views.yeni_bakim_list, name='yeni_bakim_list'),
    path('yeni-bakimlar/ekle/', arac_views.yeni_bakim_create, name='yeni_bakim_create'),
    path('yeni-bakimlar/<int:pk>/duzenle/', arac_views.yeni_bakim_update, name='yeni_bakim_update'),
    path('yeni-bakimlar/<int:pk>/sil/', arac_views.yeni_bakim_delete, name='yeni_bakim_delete'),
    
    # Uyarılar (Alerts)
    path('uyari/liste/', arac_views.uyari_list, name='uyari_list'),
    path('uyari/ekle/', arac_views.uyari_create, name='uyari_ekle'),
    path('uyari/<int:pk>/detay/', arac_views.uyari_detay, name='uyari_detay'),
    path('uyari/<int:pk>/guncelle/', arac_views.uyari_update, name='uyari_guncelle'),
    path('uyari/<int:pk>/sil/', arac_views.uyari_delete, name='uyari_delete'),
    path('uyari/<int:pk>/tamamla/', arac_views.uyari_tamamla, name='uyari_tamamla'),
    
    # Kasalar (Cash Registers)
    path('kasalar/', kasa_list, name='kasa_list'),
    path('kasalar/<int:pk>/', kasa_detail, name='kasa_detail'),
    path('kasalar/<int:pk>/pdf/', kasa_detail_pdf, name='kasa_detail_pdf'),
    path('kasalar/yeni/', kasa_create, name='kasa_create'),
    path('kasalar/<int:pk>/duzenle/', kasa_update, name='kasa_update'),
    path('kasalar/<int:pk>/sil/', kasa_delete, name='kasa_delete'),
    path('kasalar/transfer/yeni/', kasa_transfer_create, name='kasa_transfer_create'),
    path('kasa-hareketleri/yeni/', genel_hareket_create, name='genel_hareket_create'),
    path('kasa-hareketleri/<int:pk>/duzenle/', genel_hareket_update, name='genel_hareket_update'),
    path('kasa-hareketleri/<int:pk>/sil/', genel_hareket_delete, name='genel_hareket_delete'),
    
    # Masraflar (Expenses)
    path('masraflar/', masraf_list, name='masraf_list'),
    path('masraflar/yeni/', masraf_create, name='masraf_create'),
    path('masraflar/<int:pk>/duzenle/', masraf_update, name='masraf_update'),
    path('masraflar/<int:pk>/sil/', masraf_delete, name='masraf_delete'),
    path('masraflar/<int:pk>/sil/ajax/', masraf_sil, name='masraf_sil'),
    path('seferler/<int:sefer_id>/masraf/ekle/', sefer_masraf_create, name='masraf_ekle'),
    
    # API endpoints
    path('api/cities-by-country/', get_cities_by_country, name='cities_by_country'),
    path('ajax/get_exchange_rate/', get_live_exchange_rate_ajax, name='ajax_get_exchange_rate'),
    
    # Yedekleme URL'i
    path('backup/', backup_view, name='backup'),
    
    # Firma Bilgisi Kurulum
    path('firma_bilgi_kurulum/', firma_bilgi_kurulum, name='firma_bilgi_kurulum_kisa'),
    
    # Register Admin
    path('register_admin/', register_admin_view, name='register_admin'),
] 