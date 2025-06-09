"""
Cash register (Kasa) related views and operations.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q, Value, Count, Case, When, F, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import datetime, date, time
from decimal import Decimal
import json
import requests
import traceback
from .sefer_views import format_currency  # Import the format_currency function
import os

from ..models import (
    Kasalar, GenelKasaHareketi, ParaBirimleri, FaturaOdeme, 
    Faturalar, SeferMasraf, KasaTransfer, PersonelOdeme
)
from .helpers import safe_decimal, register_ttf_fonts, turkish_safe_text, get_first_two_words
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Para birimi sembolleri sözlüğü
CURRENCY_SYMBOLS = {
    'EUR': '€',
    'TRY': '₺',
    'USD': '$',
    'GBP': '£',
    'TL': '₺'  # Eski Türk Lirası kodu için de aynı sembol
}

def _resolve_currency_iso_code(para_birimi_value):
    """Helper to resolve a para_birimi_value (ID or code) to a 3-letter ISO code."""
    if not para_birimi_value:
        return "XXX" # Belirsiz veya boş
    
    pb_val_str = str(para_birimi_value)
    
    try:
        # Önce kod olarak dene
        pb = ParaBirimleri.objects.get(kod__iexact=pb_val_str) # Büyük/küçük harf duyarsız ara
        return pb.kod
    except ParaBirimleri.DoesNotExist:
        # Kod olarak bulunamazsa ve sayısal ise ID olarak dene
        if pb_val_str.isdigit():
            try:
                pb_id = int(pb_val_str)
                pb = ParaBirimleri.objects.get(id=pb_id)
                return pb.kod
            except (ParaBirimleri.DoesNotExist, ValueError):
                print(f"Warning (resolve_currency): Value '{pb_val_str}' is not a valid ParaBirimleri ID.")
                return "XXX"
        else:
            print(f"Warning (resolve_currency): Value '{pb_val_str}' is not a recognized ParaBirimleri code and not an ID.")
            return "XXX"
    except Exception as e:
        print(f"Error resolving currency for value '{pb_val_str}': {e}")
        return "XXX"

def get_exchange_rate(from_currency, to_currency):
    """Fetch exchange rate from Frankfurter.app API."""
    if from_currency == to_currency:
        return Decimal('1.0')
    try:
        # HTTPS kullandığından emin olun
        response = requests.get(f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}", timeout=5)
        response.raise_for_status()  # HTTP hataları için exception fırlatır
        data = response.json()
        rate = data.get('rates', {}).get(to_currency)
        if rate is not None:
            return Decimal(str(rate))
        else:
            print(f"Error: Rate for {to_currency} not found in API response for base {from_currency}.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rate for {from_currency} to {to_currency}: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for {from_currency} to {to_currency}.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching exchange rate: {e}")
        return None

def kasa_list(request):
    """List all cash registers."""
    kasalar_query = Kasalar.objects.all().order_by('kasa_adi')
    
    try:
        # Calculate total initial balance
        toplam_baslangic_bakiyesi = kasalar_query.aggregate(toplam=Sum('baslangic_bakiyesi'))['toplam'] or Decimal('0.0')
        
        toplam_guncel_bakiye_numeric = Decimal('0.0')

        processed_kasalar = []
        for kasa_instance in kasalar_query:
            # Get income transactions
            genel_gelir = GenelKasaHareketi.objects.filter(kasa=kasa_instance, hareket_tipi='Gelir').aggregate(
                toplam=Coalesce(Sum('tutar'), Value(Decimal('0.0'), output_field=DecimalField()))
            )['toplam']
        
            # Get expense transactions
            genel_gider = GenelKasaHareketi.objects.filter(kasa=kasa_instance, hareket_tipi='Gider').aggregate(
                toplam=Coalesce(Sum('tutar'), Value(Decimal('0.0'), output_field=DecimalField()))
            )['toplam']
        
            # Get invoice payments
            fatura_odeme = FaturaOdeme.objects.filter(Kasa=kasa_instance).aggregate(
                toplam=Coalesce(Sum('Tutar'), Value(Decimal('0.0'), output_field=DecimalField()))
            )['toplam']
        
            # Get trip expenses
            sefer_masraf = SeferMasraf.objects.filter(Kasa=kasa_instance).aggregate(
                toplam=Coalesce(Sum('TutarEUR'), Value(Decimal('0.0'), output_field=DecimalField()))
            )['toplam']
        
            # Calculate current balance
            guncel_bakiye = kasa_instance.baslangic_bakiyesi + genel_gelir - genel_gider + fatura_odeme - sefer_masraf
            kasa_instance.guncel_bakiye = guncel_bakiye
            
            # Determine currency display name and code for balance
            current_kasa_para_birimi_value = str(kasa_instance.para_birimi) if kasa_instance.para_birimi is not None else ""

            kasa_instance.currency_display_name = current_kasa_para_birimi_value
            kasa_instance.currency_code_for_balance = current_kasa_para_birimi_value

            if current_kasa_para_birimi_value:
                try:
                    pb = ParaBirimleri.objects.get(kod=current_kasa_para_birimi_value)
                    kasa_instance.currency_display_name = pb.ad
                    kasa_instance.currency_code_for_balance = pb.kod
                except ParaBirimleri.DoesNotExist:
                    if current_kasa_para_birimi_value.isdigit():
                        try:
                            pb_id = int(current_kasa_para_birimi_value)
                            pb = ParaBirimleri.objects.get(id=pb_id)
                            kasa_instance.currency_display_name = pb.ad
                            kasa_instance.currency_code_for_balance = pb.kod
                        except (ParaBirimleri.DoesNotExist, ValueError):
                            print(f"Warning (kasa_list): Kasa ID {kasa_instance.id} has para_birimi '{current_kasa_para_birimi_value}' not valid code or ID.")
                    else:
                        print(f"Warning (kasa_list): Kasa ID {kasa_instance.id} has para_birimi '{current_kasa_para_birimi_value}' not recognized code.")
                except Exception as e:
                    print(f"Error (kasa_list) looking up currency for Kasa ID {kasa_instance.id} value '{current_kasa_para_birimi_value}': {e}")
            else:
                kasa_instance.currency_display_name = "Belirtilmemiş"
                kasa_instance.currency_code_for_balance = ""

            toplam_guncel_bakiye_numeric += guncel_bakiye
            
            kasa_instance.son_hareketler = GenelKasaHareketi.objects.filter(kasa=kasa_instance).order_by('-tarih')[:3]
            processed_kasalar.append(kasa_instance)

            toplam_islem_sayisi = GenelKasaHareketi.objects.count()
        
        context = {
            'kasalar': processed_kasalar,
            'toplam_baslangic_bakiyesi': toplam_baslangic_bakiyesi,
            'toplam_guncel_bakiye': toplam_guncel_bakiye_numeric,
            'toplam_islem_sayisi': toplam_islem_sayisi,
            'today': timezone.now().date()
        }
        return render(request, 'sefer_app/kasa_list.html', context)
    except Exception as e:
        print(f"FATAL Error in kasa_list view: {e}")
        traceback.print_exc()
        messages.error(request, "Kasalar listelenirken bir sunucu hatası oluştu. Lütfen daha sonra tekrar deneyin.")
        return render(request, 'sefer_app/kasa_list.html', {'kasalar': [], 'error_message': "Kasa listesi yüklenemedi."})


def kasa_detail(request, pk):
    """Display detailed information about a specific cash register."""
    kasa = get_object_or_404(Kasalar, pk=pk)
    
    # Resolve currency name and code for the kasa
    current_kasa_para_birimi_value = str(kasa.para_birimi) if kasa.para_birimi is not None else ""
    kasa.currency_display_name = current_kasa_para_birimi_value  # Default
    kasa.currency_code = current_kasa_para_birimi_value      # Default

    if current_kasa_para_birimi_value:
        try:
            pb = ParaBirimleri.objects.get(kod=current_kasa_para_birimi_value)
            kasa.currency_display_name = pb.ad
            kasa.currency_code = pb.kod
        except ParaBirimleri.DoesNotExist:
            # Try to get the currency symbol
            try:
                currency_symbols = {
                    'EUR': '€', 'USD': '$', 'TRY': '₺', 'GBP': '£'
                }
                kasa.currency_display_name = currency_symbols.get(current_kasa_para_birimi_value, current_kasa_para_birimi_value)
                kasa.currency_code = current_kasa_para_birimi_value
            except (ParaBirimleri.DoesNotExist, ValueError):
                # Keep defaults
                pass
    
    # Common currency symbols
    CURRENCY_SYMBOLS = {
        'EUR': '€', 'USD': '$', 'TRY': '₺', 'GBP': '£'
    }
    
    # Get filter parameters
    tarih_baslangic = request.GET.get('tarih_baslangic', '')
    tarih_bitis = request.GET.get('tarih_bitis', '')
    hareket_tipi = request.GET.get('hareket_tipi', '')
    arama = request.GET.get('arama', '')
    
    # Base queryset for different transaction types
    genel_hareketler = GenelKasaHareketi.objects.filter(kasa=kasa).exclude(kategori='Personel Ödemesi').order_by('-tarih')
    fatura_odemeleri = FaturaOdeme.objects.filter(Kasa=kasa).order_by('-OdemeTarihi')
    sefer_masraflar = SeferMasraf.objects.filter(Kasa=kasa).order_by('-Tarih')
    personel_odemeleri = PersonelOdeme.objects.filter(kasa=kasa).order_by('-tarih')
    
    # Apply filters
    if tarih_baslangic:
        genel_hareketler = genel_hareketler.filter(tarih__gte=tarih_baslangic)
        fatura_odemeleri = fatura_odemeleri.filter(OdemeTarihi__gte=tarih_baslangic)
        sefer_masraflar = sefer_masraflar.filter(Tarih__gte=tarih_baslangic)
        personel_odemeleri = personel_odemeleri.filter(tarih__gte=tarih_baslangic)
    
    if tarih_bitis:
        genel_hareketler = genel_hareketler.filter(tarih__lte=tarih_bitis)
        fatura_odemeleri = fatura_odemeleri.filter(OdemeTarihi__lte=tarih_bitis)
        sefer_masraflar = sefer_masraflar.filter(Tarih__lte=tarih_bitis)
        personel_odemeleri = personel_odemeleri.filter(tarih__lte=tarih_bitis)
    
    if hareket_tipi:
        if hareket_tipi == 'Gelir':
            genel_hareketler = genel_hareketler.filter(hareket_tipi='Gelir')
            sefer_masraflar = SeferMasraf.objects.none()
            personel_odemeleri = PersonelOdeme.objects.none()
        elif hareket_tipi == 'Gider':
            genel_hareketler = genel_hareketler.filter(hareket_tipi='Gider')
            fatura_odemeleri = FaturaOdeme.objects.none()
    
    if arama:
        genel_hareketler = genel_hareketler.filter(
            Q(aciklama__icontains=arama) |
            Q(belge_no__icontains=arama)
        )
        fatura_odemeleri = fatura_odemeleri.filter(
            Q(Aciklama__icontains=arama) |
            Q(Fatura__FaturaNo__icontains=arama) |
            Q(Fatura__Firma__FirmaAdi__icontains=arama)
        )
        sefer_masraflar = sefer_masraflar.filter(
            Q(Aciklama__icontains=arama) |
            Q(BelgeNo__icontains=arama) |
            Q(Sefer__sefer_kodu__icontains=arama)
        )
        personel_odemeleri = personel_odemeleri.filter(
            Q(aciklama__icontains=arama) |
            Q(belge_no__icontains=arama) |
            Q(personel__PerAd__icontains=arama) |
            Q(personel__PerSoyad__icontains=arama)
        )
    
    # Calculate statistics
    genel_gelir = genel_hareketler.filter(hareket_tipi='Gelir').aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    genel_gider = genel_hareketler.filter(hareket_tipi='Gider').aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate current balance from initial balance
    baslangic_bakiyesi = kasa.baslangic_bakiyesi
    
    # Ensure the currency code is properly set (not an ID)
    kasa.para_birimi = _resolve_currency_iso_code(kasa.para_birimi)
    
    # Debug currency resolution
    print(f"DEBUG: Kasa para_birimi value after resolution: '{kasa.para_birimi}'")
    print(f"DEBUG: Currency symbol would be: {CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)}")
    
    # Calculate total income from invoice payments (add to balance)
    fatura_odeme_toplam = fatura_odemeleri.aggregate(
        toplam=Sum('Tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate total expenses from trip expenses (subtract from balance)
    sefer_masraf_toplam = sefer_masraflar.aggregate(
        toplam=Sum('TutarEUR', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate total expenses from personnel payments (subtract from balance)
    personel_odeme_toplam = personel_odemeleri.aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate net current balance
    guncel_bakiye = baslangic_bakiyesi + genel_gelir - genel_gider + fatura_odeme_toplam - sefer_masraf_toplam - personel_odeme_toplam
    
    # Calculate total income and expenses for comparison
    toplam_gelir_genel = genel_gelir + fatura_odeme_toplam
    toplam_gider_genel = genel_gider + sefer_masraf_toplam + personel_odeme_toplam
    
    # Prepare a combined list of all transactions with consistent field names
    all_transactions = []
    
    # Add general transactions
    for hareket in genel_hareketler:
        # Format the amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{hareket.tutar:.2f} {kasa_symbol}"
        
        all_transactions.append({
            'id': hareket.id, 
            'tarih': hareket.tarih, 
            'aciklama': hareket.aciklama,
            'hareket_tipi': hareket.hareket_tipi, 
            'tutar': hareket.tutar,
            'tutar_display': amount_display,
            'belge_no': hareket.belge_no, 
            'kaynak': 'Genel Hareket', 
            'link': None,
            'gider_turu': hareket.gider_turu if hareket.hareket_tipi == 'Gider' else ''
        })
        
    # Add invoice payments
    for odeme in fatura_odemeleri:
        fatura_info = ""
        fatura_link = None
        transaction_type = "Fatura Ödemesi"  # Default for 'Alış' (Purchase) invoices
        
        if odeme.Fatura:
            fatura_link = f"/faturalar/{odeme.Fatura.id}/"
            
            # Use different description based on invoice type
            if odeme.Fatura.FaturaTipi in ['Satış', 'Nakliye']:
                transaction_type = "Fatura Tahsilatı"
                
            if odeme.Fatura.Sefer:
                fatura_info = f"Sefer: {odeme.Fatura.Sefer.sefer_kodu}"
        
        # Format the payment amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{odeme.Tutar:.2f} {kasa_symbol}"
        
        all_transactions.append({
            'id': odeme.id,
            'tarih': odeme.OdemeTarihi,
            'aciklama': f"{transaction_type} - {fatura_info}".strip(" - "),
            'hareket_tipi': 'Gelir',
            'tutar': odeme.Tutar,
            'tutar_display': amount_display,
            'belge_no': odeme.Fatura.FaturaNo if odeme.Fatura else '',
            'kaynak': 'Fatura Ödeme',
            'link': fatura_link,
            'gider_turu': ''
        })
        
    # Add trip expenses in the requested format
    for masraf in sefer_masraflar:
        sefer_link = None
        route_info = ""
        
        if masraf.Sefer:
            # Get trip code and country codes
            sefer_link = f"/seferler/{masraf.Sefer.id}/"
            
            # Get country codes for route
            baslangic_ulke = getattr(masraf.Sefer, 'baslangic_ulkesi', None)
            bitis_ulke = getattr(masraf.Sefer, 'bitis_ulkesi', None)
            
            baslangic_kod = getattr(baslangic_ulke, 'ulke_kodu', 'TR') if baslangic_ulke else 'TR'
            bitis_kod = getattr(bitis_ulke, 'ulke_kodu', 'AT') if bitis_ulke else 'AT'
            
            # Format as requested: sefer_kodu - origin_country_code - destination_country_code
            route_info = f"{masraf.Sefer.sefer_kodu} - {baslangic_kod} - {bitis_kod}"
        
        # Format the expense amount with original currency info if different from the cash register
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{masraf.TutarEUR:.2f} {kasa_symbol}"
        
        if masraf.ParaBirimi != kasa.para_birimi:
            original_symbol = CURRENCY_SYMBOLS.get(masraf.ParaBirimi, masraf.ParaBirimi)
            amount_display = f"{masraf.TutarEUR:.2f} {kasa_symbol} [{masraf.Tutar:.2f} {original_symbol}]"
        
        all_transactions.append({
            'id': masraf.id,
            'tarih': masraf.Tarih,
            'aciklama': route_info,  # sefer_kodu - country_code - country_code
            'hareket_tipi': 'Gider',
            'tutar': masraf.TutarEUR,
            'tutar_display': amount_display,
            'belge_no': masraf.BelgeNo,  # Use the actual BelgeNo
            'kaynak': 'Sefer Masrafı',
            'link': sefer_link,
            'gider_turu': masraf.MasrafTipi or ''
        })
        
    # Add personnel payments
    for odeme in personel_odemeleri:
        personel_link = f"/personeller/{odeme.personel.id}/"
        personel_name = f"{odeme.personel.PerAd} {odeme.personel.PerSoyad}"
        
        # Format the payment amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{odeme.tutar:.2f} {kasa_symbol}"
        
        # Combine personnel name and description
        combined_description = personel_name
        if odeme.aciklama and odeme.aciklama.strip():
            combined_description = f"{personel_name} - {odeme.aciklama}"
        
        all_transactions.append({
            'id': odeme.id,
            'tarih': odeme.tarih,
            'aciklama': combined_description,  # Personnel name + description
            'hareket_tipi': 'Gider',
            'tutar': odeme.tutar,
            'tutar_display': amount_display,
            'belge_no': odeme.belge_no,
            'kaynak': 'Personel Ödemesi',
            'link': personel_link,
            'gider_turu': odeme.odeme_turu  # Payment type
        })

    # Properly handle both datetime and date objects for sorting
    def get_date_time_tuple(dt_obj):
        if isinstance(dt_obj, datetime):
            return (dt_obj.date(), dt_obj.time())
        elif isinstance(dt_obj, date):
            return (dt_obj, time(0, 0, 0))  # Minimum time (00:00:00)
        else:
            return (dt_obj, None)
    
    chronological_transactions = sorted(all_transactions, key=lambda x: get_date_time_tuple(x['tarih']))
    
    # Sort again by date and time for display (newest first)
    all_transactions = sorted(chronological_transactions, key=lambda x: get_date_time_tuple(x['tarih']), reverse=True)
    
    page = request.GET.get('page', 1)
    paginator = Paginator(all_transactions, 25)
    try:
        hareketler = paginator.page(page)
    except PageNotAnInteger:
        hareketler = paginator.page(1)
    except EmptyPage:
        hareketler = paginator.page(paginator.num_pages)
    
    context = {
        'kasa': kasa, # kasa object now has .currency_display_name and .currency_code
        'hareketler': hareketler,
        'toplam_gelir': toplam_gelir_genel,
        'toplam_gider': toplam_gider_genel,
        'baslangic_bakiyesi': baslangic_bakiyesi,
        'guncel_bakiye': guncel_bakiye,
        'tarih_baslangic': tarih_baslangic,
        'tarih_bitis': tarih_bitis,
        'hareket_tipi': hareket_tipi,
        'arama': arama,
        'today': timezone.now().date(),
        'has_hareketler': bool(all_transactions)
    }
    return render(request, 'sefer_app/kasa_detail.html', context)


def kasa_detail_pdf(request, pk):
    """Generate PDF report of cash register transactions."""
    kasa = get_object_or_404(Kasalar, pk=pk)
    
    # Filter parameters - reuse the same filters from the kasa_detail view
    tarih_baslangic = request.GET.get('tarih_baslangic', '')
    tarih_bitis = request.GET.get('tarih_bitis', '')
    hareket_tipi = request.GET.get('hareket_tipi', '')
    
    # Base queryset for different transaction types
    genel_hareketler = GenelKasaHareketi.objects.filter(kasa=kasa).exclude(kategori='Personel Ödemesi').order_by('-tarih')
    fatura_odemeleri = FaturaOdeme.objects.filter(Kasa=kasa).order_by('-OdemeTarihi')
    sefer_masraflar = SeferMasraf.objects.filter(Kasa=kasa).order_by('-Tarih')
    personel_odemeleri = PersonelOdeme.objects.filter(kasa=kasa).order_by('-tarih')
    
    # Apply filters
    if tarih_baslangic:
        genel_hareketler = genel_hareketler.filter(tarih__gte=tarih_baslangic)
        fatura_odemeleri = fatura_odemeleri.filter(OdemeTarihi__gte=tarih_baslangic)
        sefer_masraflar = sefer_masraflar.filter(Tarih__gte=tarih_baslangic)
        personel_odemeleri = personel_odemeleri.filter(tarih__gte=tarih_baslangic)
    
    if tarih_bitis:
        genel_hareketler = genel_hareketler.filter(tarih__lte=tarih_bitis)
        fatura_odemeleri = fatura_odemeleri.filter(OdemeTarihi__lte=tarih_bitis)
        sefer_masraflar = sefer_masraflar.filter(Tarih__lte=tarih_bitis)
        personel_odemeleri = personel_odemeleri.filter(tarih__lte=tarih_bitis)
    
    if hareket_tipi:
        if hareket_tipi == 'Gelir':
            genel_hareketler = genel_hareketler.filter(hareket_tipi='Gelir')
            sefer_masraflar = SeferMasraf.objects.none()
            personel_odemeleri = PersonelOdeme.objects.none()
        elif hareket_tipi == 'Gider':
            genel_hareketler = genel_hareketler.filter(hareket_tipi='Gider')
            fatura_odemeleri = FaturaOdeme.objects.none()
    
    # Calculate statistics
    genel_gelir = genel_hareketler.filter(hareket_tipi='Gelir').aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    genel_gider = genel_hareketler.filter(hareket_tipi='Gider').aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate from initial balance
    baslangic_bakiyesi = kasa.baslangic_bakiyesi
    
    # Calculate total income from invoice payments (add to balance)
    fatura_odeme_toplam = fatura_odemeleri.aggregate(
        toplam=Sum('Tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate total expenses from trip expenses (subtract from balance)
    sefer_masraf_toplam = sefer_masraflar.aggregate(
        toplam=Sum('TutarEUR', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate total expenses from personnel payments (subtract from balance)
    personel_odeme_toplam = personel_odemeleri.aggregate(
        toplam=Sum('tutar', default=0)
    )['toplam'] or Decimal('0.00')
    
    # Calculate net current balance
    guncel_bakiye = baslangic_bakiyesi + genel_gelir - genel_gider + fatura_odeme_toplam - sefer_masraf_toplam - personel_odeme_toplam
    
    # Calculate total income (general income + invoice payments)
    toplam_gelir = genel_gelir + fatura_odeme_toplam
    
    # Calculate total expenses (general expenses + trip expenses + personnel expenses)
    toplam_gider = genel_gider + sefer_masraf_toplam + personel_odeme_toplam
    
    # Prepare a combined list of all transactions with consistent field names
    all_transactions = []
    
    # Add general transactions
    for hareket in genel_hareketler:
        # Format the amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{hareket.tutar:.2f} {kasa_symbol}"
        
        all_transactions.append({
            'id': hareket.id, 
            'tarih': hareket.tarih, 
            'aciklama': hareket.aciklama,
            'hareket_tipi': hareket.hareket_tipi, 
            'tutar': hareket.tutar,
            'tutar_display': amount_display,
            'belge_no': hareket.belge_no, 
            'kaynak': 'Genel Hareket', 
            'link': None,
            'gider_turu': hareket.gider_turu if hareket.hareket_tipi == 'Gider' else ''
        })
    
    # Add invoice payments
    for odeme in fatura_odemeleri:
        fatura_info = ""
        fatura_link = None
        transaction_type = "Fatura Ödemesi"  # Default for 'Alış' (Purchase) invoices
        
        if odeme.Fatura:
            fatura_link = f"/faturalar/{odeme.Fatura.id}/"
            
            # Use different description based on invoice type
            if odeme.Fatura.FaturaTipi in ['Satış', 'Nakliye']:
                transaction_type = "Fatura Tahsilatı"
                
            if odeme.Fatura.Sefer:
                fatura_info = f"Sefer: {odeme.Fatura.Sefer.sefer_kodu}"
        
        # Format the amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{odeme.Tutar:.2f} {kasa_symbol}"
        
        all_transactions.append({
            'id': odeme.id,
            'tarih': odeme.OdemeTarihi,
            'aciklama': f"{transaction_type} - {fatura_info}".strip(" - "),
            'hareket_tipi': 'Gelir',
            'tutar': odeme.Tutar,
            'tutar_display': amount_display,
            'belge_no': odeme.Fatura.FaturaNo if odeme.Fatura else '',
            'kaynak': 'Fatura Ödeme',
            'link': fatura_link,
            'gider_turu': ''
        })
    
    # Add trip expenses
    for masraf in sefer_masraflar:
        sefer_link = None
        route_info = ""
        
        if masraf.Sefer:
            sefer_link = f"/seferler/{masraf.Sefer.id}/"
            
            # Format trip info with city names and country codes
            if hasattr(masraf.Sefer, 'guzergah') and masraf.Sefer.guzergah:
                route_info = masraf.Sefer.guzergah
            else:
                baslangic_ulke = getattr(masraf.Sefer, 'baslangic_ulkesi', None)
                bitis_ulke = getattr(masraf.Sefer, 'bitis_ulkesi', None)
                
                baslangic_kod = getattr(baslangic_ulke, 'ulke_kodu', 'TR') if baslangic_ulke else 'TR'
                bitis_kod = getattr(bitis_ulke, 'ulke_kodu', 'AT') if bitis_ulke else 'AT'
                
                # Format as requested: sefer_kodu - origin_country_code - destination_country_code
                route_info = f"{masraf.Sefer.sefer_kodu} - {baslangic_kod} - {bitis_kod}"
        
        # Format the amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{masraf.TutarEUR:.2f} {kasa_symbol}"
        
        all_transactions.append({
            'id': masraf.id,
            'tarih': masraf.Tarih,
            'aciklama': route_info,
            'hareket_tipi': 'Gider',
            'tutar': masraf.TutarEUR,
            'tutar_display': amount_display,
            'belge_no': masraf.BelgeNo,
            'kaynak': 'Sefer Masrafı',
            'link': sefer_link,
            'gider_turu': masraf.MasrafTipi or ''
        })
        
    # Add personnel payments
    for odeme in personel_odemeleri:
        personel_link = f"/personeller/{odeme.personel.id}/"
        personel_name = f"{odeme.personel.PerAd} {odeme.personel.PerSoyad}"
        
        # Format the payment amount with currency symbol
        kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
        amount_display = f"{odeme.tutar:.2f} {kasa_symbol}"
        
        # Combine personnel name and description
        combined_description = personel_name
        if odeme.aciklama and odeme.aciklama.strip():
            combined_description = f"{personel_name} - {odeme.aciklama}"
        
        all_transactions.append({
            'id': odeme.id,
            'tarih': odeme.tarih,
            'aciklama': combined_description,  # Personnel name + description
            'hareket_tipi': 'Gider',
            'tutar': odeme.tutar,
            'tutar_display': amount_display,
            'belge_no': odeme.belge_no,
            'kaynak': 'Personel Ödemesi',
            'link': personel_link,
            'gider_turu': odeme.odeme_turu  # Payment type
        })

    # Sort transactions by date and time, not just date
    # If date and time are in the same tarih field, this will sort by both
    all_transactions.sort(key=lambda x: x['tarih'], reverse=True)
    
    # Properly handle both datetime and date objects for sorting
    def get_date_time_tuple(dt_obj):
        if isinstance(dt_obj, datetime):
            return (dt_obj.date(), dt_obj.time())
        elif isinstance(dt_obj, date):
            return (dt_obj, time(0, 0, 0))  # Minimum time (00:00:00)
        else:
            return (dt_obj, None)
    
    chronological_transactions = sorted(all_transactions, key=lambda x: get_date_time_tuple(x['tarih']))
    
    # Sort again by date and time for display (newest first)
    all_transactions = sorted(chronological_transactions, key=lambda x: get_date_time_tuple(x['tarih']), reverse=True)
    
    # Create PDF document
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{turkish_safe_text(kasa.kasa_adi)}_rapor.pdf"'
    
    # Register fonts with Turkish character support
    font_name = register_ttf_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    # Create document
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
    
    # Create custom styles with Turkish character support
    title_style = ParagraphStyle(
        name='TitleStyle', 
        parent=styles['Heading1'], 
        alignment=TA_CENTER,
        fontName=font_bold
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontName=font_name
    )
    
    # Create content elements
    elements = []
    
    # Title
    elements.append(Paragraph(turkish_safe_text(f"{kasa.kasa_adi} - Kasa Raporu"), title_style))
    
    # Date range info
    if tarih_baslangic and tarih_bitis:
        date_info = turkish_safe_text(f"Dönem: {tarih_baslangic} - {tarih_bitis}")
    else:
        date_info = turkish_safe_text("Tüm Dönemler")
    
    elements.append(Paragraph(date_info, normal_style))
    elements.append(Paragraph(turkish_safe_text(f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), normal_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Get currency name for display
    para_birimi_adi = kasa.para_birimi
    try:
        # Önce ID olarak dene
        if str(kasa.para_birimi).isdigit():
            para_birimi_obj = ParaBirimleri.objects.get(id=int(kasa.para_birimi))
            para_birimi_adi = para_birimi_obj.ad
        else:
            # Kod olarak dene (EUR, TRY gibi)
            para_birimi_obj = ParaBirimleri.objects.get(kod=kasa.para_birimi)
            para_birimi_adi = para_birimi_obj.ad
    except (ParaBirimleri.DoesNotExist, ValueError, Exception) as e:
        # Fallback to code if name can't be retrieved
        print(f"DEBUG: Para birimi adı bulunamadı: {kasa.para_birimi}, Hata: {str(e)}")
    
    # Currency symbol for formatting
    kasa_symbol = CURRENCY_SYMBOLS.get(kasa.para_birimi, kasa.para_birimi)
    
    # Summary table
    summary_data = [
        [turkish_safe_text("Özet Bilgiler"), ""],
        [turkish_safe_text("Para Birimi:"), turkish_safe_text(para_birimi_adi)],
        [turkish_safe_text("Başlangıç Bakiye:"), f"{format_currency(baslangic_bakiyesi)} {para_birimi_adi}"],
        [turkish_safe_text("Toplam Gelir:"), f"{format_currency(toplam_gelir)} {para_birimi_adi}"],
        [turkish_safe_text("Toplam Gider:"), f"{format_currency(toplam_gider)} {para_birimi_adi}"],
        [turkish_safe_text("Net Nakit Akışı:"), f"{format_currency(toplam_gelir - toplam_gider)} {para_birimi_adi}"],
        [turkish_safe_text("Güncel Bakiye:"), f"{format_currency(guncel_bakiye)} {para_birimi_adi}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Transaction detail table
    elements.append(Paragraph(turkish_safe_text("Hareket Listesi"), title_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Define table headers
    transaction_data = [[turkish_safe_text("Tarih"), turkish_safe_text("Belge No"), turkish_safe_text("Açıklama"), turkish_safe_text("Kaynak"), turkish_safe_text("Giriş"), turkish_safe_text("Çıkış")]]
    
    # Add transaction data to table
    for hareket in all_transactions:
        gelir = ""
        gider = ""
        
        if hareket['hareket_tipi'] == 'Gelir':
            gelir = f"{format_currency(hareket['tutar'])} {para_birimi_adi}"
        else:
            gider = f"{format_currency(hareket['tutar'])} {para_birimi_adi}"
        
        tarih_str = hareket['tarih'].strftime("%d.%m.%Y")
        
        transaction_data.append([
            tarih_str,
            hareket['belge_no'] or "-",
            turkish_safe_text(hareket['aciklama']),
            turkish_safe_text(hareket['kaynak']),
            gelir,
            gider
        ])
    
    # Create table with auto-calculated widths
    col_widths = [2*cm, 2.5*cm, 6*cm, 2.5*cm, 2*cm, 2*cm]
    transaction_table = Table(transaction_data, colWidths=col_widths, repeatRows=1)
    
    # Set table style
    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(transaction_table)
    
    # Add footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(turkish_safe_text(f"© {datetime.now().year} NextSefer - Kasa Raporu"), normal_style))
    
    # Build the PDF
    doc.build(elements)
    
    return response


def kasa_create(request):
    """Create a new cash register."""
    para_birimleri = ParaBirimleri.objects.all().order_by('kod')
    kasa_tipi_choices = Kasalar.KASA_TIPI_CHOICES
    
    if request.method == 'POST':
        try:
            kasa_adi = request.POST.get('kasa_adi')
            kasa_tipi = request.POST.get('kasa_tipi')
            para_birimi = request.POST.get('para_birimi')
            baslangic_bakiyesi = safe_decimal(request.POST.get('baslangic_bakiyesi', '0'))
            aciklama = request.POST.get('aciklama', '')
            
            # Basic validation
            if not kasa_adi:
                raise ValueError("Kasa adı boş olamaz")
            
            # Create the cash register
            kasa = Kasalar(
                kasa_adi=kasa_adi,
                kasa_tipi=kasa_tipi,
                para_birimi=para_birimi,
                baslangic_bakiyesi=baslangic_bakiyesi,
                aciklama=aciklama
            )
            kasa.save()
                
            messages.success(request, f"'{kasa_adi}' kasası başarıyla oluşturuldu.")
            return redirect('kasa_detail', pk=kasa.pk)
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Kasa oluşturulurken bir hata oluştu: {str(e)}")
    
    context = {
        'para_birimleri': para_birimleri,
        'kasa_tipi_choices': kasa_tipi_choices,
    }
    return render(request, 'sefer_app/kasa_form.html', context)


def kasa_update(request, pk):
    """Update an existing cash register."""
    kasa = get_object_or_404(Kasalar, pk=pk)
    para_birimleri = ParaBirimleri.objects.all().order_by('kod')
    kasa_tipi_choices = Kasalar.KASA_TIPI_CHOICES
    
    if request.method == 'POST':
        try:
            kasa.kasa_adi = request.POST.get('kasa_adi')
            kasa.kasa_tipi = request.POST.get('kasa_tipi')
            kasa.para_birimi = request.POST.get('para_birimi')
            kasa.baslangic_bakiyesi = safe_decimal(request.POST.get('baslangic_bakiyesi', '0'))
            kasa.aciklama = request.POST.get('aciklama', '')
            
            # Basic validation
            if not kasa.kasa_adi:
                raise ValueError("Kasa adı boş olamaz")
            
            # Save the updated cash register
            kasa.save()
            
            messages.success(request, f"'{kasa.kasa_adi}' kasası başarıyla güncellendi.")
            return redirect('kasa_detail', pk=kasa.pk)
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Kasa güncellenirken bir hata oluştu: {str(e)}")
    
    context = {
        'kasa': kasa,
        'para_birimleri': para_birimleri,
        'kasa_tipi_choices': kasa_tipi_choices,
    }
    return render(request, 'sefer_app/kasa_form.html', context)


def kasa_delete(request, pk):
    """Delete a cash register."""
    kasa = get_object_or_404(Kasalar, pk=pk)
    
    # Count related transactions
    hareket_sayisi = GenelKasaHareketi.objects.filter(kasa=kasa).count()
    
    # Calculate current balance
    genel_gelir = GenelKasaHareketi.objects.filter(kasa=kasa, hareket_tipi='Gelir').aggregate(
        toplam=Coalesce(Sum('tutar'), Value(0, output_field=DecimalField()))
    )['toplam'] or 0
    
    genel_gider = GenelKasaHareketi.objects.filter(kasa=kasa, hareket_tipi='Gider').aggregate(
        toplam=Coalesce(Sum('tutar'), Value(0, output_field=DecimalField()))
    )['toplam'] or 0
    
    fatura_odeme = FaturaOdeme.objects.filter(Kasa=kasa).aggregate(
        toplam=Coalesce(Sum('Tutar'), Value(0, output_field=DecimalField()))
    )['toplam'] or 0
    
    sefer_masraf = SeferMasraf.objects.filter(Kasa=kasa).aggregate(
        toplam=Coalesce(Sum('TutarEUR'), Value(0, output_field=DecimalField()))
    )['toplam'] or 0
    
    guncel_bakiye = kasa.baslangic_bakiyesi + genel_gelir - genel_gider + fatura_odeme - sefer_masraf
    
    if request.method == 'POST':
        try:
            # Check if there are related transactions
            if hareket_sayisi > 0:
                messages.error(
                    request,
                    f"Bu kasada {hareket_sayisi} hareket kaydı bulunduğu için silinemez."
                )
                return redirect('kasa_detail', pk=pk)
            
            kasa_adi = kasa.kasa_adi
            kasa.delete()
            messages.success(request, f"'{kasa_adi}' kasası başarıyla silindi.")
            return redirect('kasa_list')
            
        except Exception as e:
            messages.error(request, f'Kasa silme hatası: {str(e)}')
            return redirect('kasa_detail', pk=pk)
    
    context = {
        'kasa': kasa,
        'hareket_sayisi': hareket_sayisi,
        'guncel_bakiye': guncel_bakiye,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/kasa_confirm_delete.html', context)


def kasa_transfer_create(request):
    kasalar_query = Kasalar.objects.all().order_by('kasa_adi')
    para_birimleri_all = ParaBirimleri.objects.filter(aktif=True)

    print("kasa_transfer_create called")

    kasalar_list_for_template = []
    for kasa_obj in kasalar_query:
        kasa_obj.resolved_currency_code = _resolve_currency_iso_code(kasa_obj.para_birimi)
        kasalar_list_for_template.append(kasa_obj)
    
    form_data_on_error = {}
    if request.method == 'POST':
        try:
            print("Processing POST data:", request.POST.dict())  # Debug POST data
            kaynak_kasa_id = request.POST.get('kaynak_kasa')
            hedef_kasa_id = request.POST.get('hedef_kasa')
            tutar_str = request.POST.get('tutar', '0')
            tarih_str = request.POST.get('tarih', timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
            aciklama = request.POST.get('aciklama', '')

            form_data_on_error = {
                'kaynak_kasa_form_id': kaynak_kasa_id,
                'hedef_kasa_form_id': hedef_kasa_id,
                'tutar_form': tutar_str,
                'aciklama_form': aciklama,
                'tarih_form': tarih_str
            }
            print(f"Form data extracted: {form_data_on_error}")

            tutar = safe_decimal(tutar_str)
            print(f"Parsed tutar: {tutar}")
            
            if not kaynak_kasa_id or not hedef_kasa_id:
                messages.error(request, 'Kaynak ve hedef kasa seçimi zorunludur.')
                context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                return render(request, 'sefer_app/kasa_transfer_form.html', context)
            if kaynak_kasa_id == hedef_kasa_id:
                messages.error(request, 'Kaynak ve hedef kasa aynı olamaz.')
                context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                return render(request, 'sefer_app/kasa_transfer_form.html', context)
            if tutar <= 0:
                messages.error(request, 'Transfer tutarı pozitif olmalıdır.')
                context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                return render(request, 'sefer_app/kasa_transfer_form.html', context)
            
            kaynak_kasa = Kasalar.objects.get(id=kaynak_kasa_id)
            hedef_kasa = Kasalar.objects.get(id=hedef_kasa_id)
            
            try:
                tarih = datetime.strptime(tarih_str, '%Y-%m-%d %H:%M:%S')
                if timezone.is_naive(tarih): tarih = timezone.make_aware(tarih, timezone.get_current_timezone())
                print(f"Parsed tarih: {tarih}")
            except ValueError:
                try: 
                    tarih_dt_obj = datetime.strptime(tarih_str, '%Y-%m-%d').date()
                    tarih = datetime.combine(tarih_dt_obj, datetime.min.time())
                    if timezone.is_naive(tarih): tarih = timezone.make_aware(tarih, timezone.get_current_timezone())
                    print(f"Parsed tarih (date only): {tarih}")
                except ValueError:
                    print(f"Error parsing date: {tarih_str}")
                    messages.error(request, "Geçersiz tarih formatı.")
                    context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                    return render(request, 'sefer_app/kasa_transfer_form.html', context)

            kur = Decimal('1.0')
            hedef_tutar = tutar

            kaynak_kasa_currency_code = _resolve_currency_iso_code(kaynak_kasa.para_birimi)
            hedef_kasa_currency_code = _resolve_currency_iso_code(hedef_kasa.para_birimi)
            print(f"Currency codes: {kaynak_kasa_currency_code} to {hedef_kasa_currency_code}")

            if kaynak_kasa_currency_code == "XXX" or hedef_kasa_currency_code == "XXX":
                messages.error(request, "Kaynak veya hedef kasanın para birimi kodu anlaşılamadı.")
                context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                return render(request, 'sefer_app/kasa_transfer_form.html', context)

            if kaynak_kasa_currency_code != hedef_kasa_currency_code:
                fetched_kur = get_exchange_rate(kaynak_kasa_currency_code, hedef_kasa_currency_code)
                if fetched_kur is None:
                    messages.error(request, f"{kaynak_kasa_currency_code} -> {hedef_kasa_currency_code} için kur bilgisi alınamadı. Lütfen API bağlantısını kontrol edin veya daha sonra tekrar deneyin.")
                    context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                    return render(request, 'sefer_app/kasa_transfer_form.html', context)
                kur = fetched_kur
                hedef_tutar = tutar * kur
            
            kaynak_gelir = GenelKasaHareketi.objects.filter(kasa=kaynak_kasa, hareket_tipi='Gelir').aggregate(toplam=Coalesce(Sum('tutar'), Decimal(0)))['toplam']
            kaynak_gider = GenelKasaHareketi.objects.filter(kasa=kaynak_kasa, hareket_tipi='Gider').aggregate(toplam=Coalesce(Sum('tutar'), Decimal(0)))['toplam']
            kaynak_fatura_odeme_gelir = FaturaOdeme.objects.filter(Kasa=kaynak_kasa, Fatura__FaturaTipi__in=['Satış', 'Nakliye']).aggregate(toplam=Coalesce(Sum('Tutar'), Decimal(0)))['toplam']
            kaynak_fatura_odeme_gider = FaturaOdeme.objects.filter(Kasa=kaynak_kasa, Fatura__FaturaTipi='Alış').aggregate(toplam=Coalesce(Sum('Tutar'), Decimal(0)))['toplam']
            kaynak_sefer_masraf = SeferMasraf.objects.filter(Kasa=kaynak_kasa).aggregate(toplam=Coalesce(Sum('TutarEUR'), Decimal(0)))['toplam']
            kaynak_bakiye = (kaynak_kasa.baslangic_bakiyesi + kaynak_gelir + kaynak_fatura_odeme_gelir - kaynak_gider - kaynak_fatura_odeme_gider - kaynak_sefer_masraf)

            if kaynak_bakiye < tutar:
                messages.error(request, f"Yetersiz bakiye! {kaynak_kasa.kasa_adi} kasasında {kaynak_bakiye:.2f} {kaynak_kasa_currency_code} var, transfer tutarı {tutar:.2f} {kaynak_kasa_currency_code}.")
                context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
                return render(request, 'sefer_app/kasa_transfer_form.html', context)

            # Generate transfer document number
            try:
                transfer_belge_no = generate_transfer_belge_no()
                print(f"Generated transfer document code: {transfer_belge_no}")
            except Exception as e:
                print(f"Error generating doc code: {str(e)}")
                transfer_belge_no = f"TRA-TEMP-{timezone.now().strftime('%H%M%S')}"
                print(f"Using fallback document code: {transfer_belge_no}")

            try:
                transfer = KasaTransfer.objects.create(
                    kaynak_kasa=kaynak_kasa,
                    hedef_kasa=hedef_kasa,
                    tutar=tutar,
                    tarih=tarih,
                    aciklama=aciklama,
                    kur=kur 
                )
                print(f"Created transfer object: {transfer.id}")
                
                gkh_kaynak = GenelKasaHareketi.objects.create(
                    kasa=kaynak_kasa,
                    hareket_tipi='Gider',
                    kategori='Kasa Transferi (Çıkış)',
                    tutar=tutar,
                    tarih=tarih,
                    belge_no=transfer_belge_no,
                    aciklama=f"Transfer -> {hedef_kasa.kasa_adi} ({hedef_kasa_currency_code}). {aciklama}"
                )
                print(f"Created source transaction: {gkh_kaynak.id}")
                
                gkh_hedef = GenelKasaHareketi.objects.create(
                    kasa=hedef_kasa,
                    hareket_tipi='Gelir',
                    kategori='Kasa Transferi (Giriş)',
                    tutar=hedef_tutar.quantize(Decimal('0.01')), 
                    tarih=tarih,
                    belge_no=transfer_belge_no,
                    aciklama=f"Transfer <- {kaynak_kasa.kasa_adi} ({kaynak_kasa_currency_code}). {aciklama}"
                )
                print(f"Created destination transaction: {gkh_hedef.id}")
            except Exception as e:
                print(f"Error creating transfer records: {str(e)}")
                traceback.print_exc()
                raise
            
            if kaynak_kasa_currency_code == hedef_kasa_currency_code:
                success_msg = f"{tutar:.2f} {kaynak_kasa_currency_code} başarıyla {kaynak_kasa.kasa_adi} kasasından {hedef_kasa.kasa_adi} kasasına transfer edildi."
            else:
                success_msg = f"{tutar:.2f} {kaynak_kasa_currency_code} başarıyla {kaynak_kasa.kasa_adi} kasasından {hedef_tutar:.2f} {hedef_kasa_currency_code} olarak {hedef_kasa.kasa_adi} kasasına transfer edildi. (Kur: {kur:.4f})"
            
            messages.success(request, success_msg)
            return redirect('kasa_list')
            
        except Kasalar.DoesNotExist:
            messages.error(request, "Seçilen kasa veya kasalar bulunamadı.")
            context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
            return render(request, 'sefer_app/kasa_transfer_form.html', context)
        except Exception as e:
            print(f"Error in transfer: {str(e)}")
            traceback.print_exc()
            messages.error(request, f'Transfer sırasında beklenmedik bir hata oluştu: {str(e)}')
            context = {'kasalar': kasalar_list_for_template, 'para_birimleri': para_birimleri_all, 'today': timezone.now().date(), **form_data_on_error}
            return render(request, 'sefer_app/kasa_transfer_form.html', context)
    else: # GET request
        context = {
            'kasalar': kasalar_list_for_template, 
            'para_birimleri': para_birimleri_all, 
            'today': timezone.now().date()
        }
        return render(request, 'sefer_app/kasa_transfer_form.html', context)


def generate_transfer_belge_no():
    """Generate a document number in the format TRA-MMYY-XXXX."""
    today = datetime.now()
    month_year = f"{today.month:02d}{str(today.year)[-2:]}"  # MMYY format
    prefix = f"TRA-{month_year}-"
    
    # Check for existing document numbers with this prefix
    latest_transfer = GenelKasaHareketi.objects.filter(
        belge_no__startswith=prefix,
        kategori__in=['Kasa Transferi (Çıkış)', 'Kasa Transferi (Giriş)']
    ).order_by('-belge_no').first()
    
    if latest_transfer and latest_transfer.belge_no and len(latest_transfer.belge_no) >= len(prefix) + 4:
        try:
            # Extract the numeric part and increment
            number_part = latest_transfer.belge_no[len(prefix):]
            number = int(number_part) + 1
        except (ValueError, IndexError):
            # If parsing fails, start from 1
            number = 1
    else:
        # No existing document, start from 1
        number = 1
    
    # Format with leading zeros to ensure 4 digits
    return f"{prefix}{number:04d}"


def generate_kasa_belge_no():
    """Generate a document number in the format KAS-MMYY-XXXX."""
    today = datetime.now()
    month_year = f"{today.month:02d}{str(today.year)[-2:]}"  # MMYY format
    prefix = f"KAS-{month_year}-"
    
    # Check for existing document numbers with this prefix
    latest_kasa = GenelKasaHareketi.objects.filter(
        belge_no__startswith=prefix
    ).order_by('-belge_no').first()
    
    if latest_kasa and latest_kasa.belge_no and len(latest_kasa.belge_no) >= len(prefix) + 4:
        try:
            # Extract the numeric part and increment
            number_part = latest_kasa.belge_no[len(prefix):]
            number = int(number_part) + 1
        except (ValueError, IndexError):
            # If parsing fails, start from 1
            number = 1
    else:
        # No existing document, start from 1
        number = 1
    
    # Format with leading zeros to ensure 4 digits
    return f"{prefix}{number:04d}"


def genel_hareket_create(request):
    """Create a general transaction for a cash register."""
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    print("genel_hareket_create called")
    
    if request.method == 'POST':
        try:
            print("Processing POST data:", request.POST)
            kasa_id = request.POST.get('kasa')
            hareket_tipi = request.POST.get('hareket_tipi')
            kategori = request.POST.get('kategori', '')
            gider_turu = request.POST.get('gider_turu', '')
            tutar_raw = request.POST.get('tutar', '0')
            print(f"Received tutar_raw: {tutar_raw}")
            tutar = safe_decimal(tutar_raw)
            print(f"Converted tutar: {tutar}")
            tarih = request.POST.get('tarih')
            belge_no = request.POST.get('belge_no', '')
            aciklama = request.POST.get('aciklama', '')
            
            if not kasa_id or not hareket_tipi:
                messages.error(request, 'Kasa ve hareket tipi seçimi zorunludur.')
                print("Error: Kasa or hareket_tipi missing")
                return render(request, 'sefer_app/genel_hareket_form.html', {'kasalar': kasalar})
                
            if tutar <= 0:
                messages.error(request, 'Tutar pozitif olmalıdır.')
                print(f"Error: Tutar is not positive: {tutar}")
                return render(request, 'sefer_app/genel_hareket_form.html', {'kasalar': kasalar})
            
            # Get cash register
            kasa = Kasalar.objects.get(id=kasa_id)
            print(f"Found kasa: {kasa.kasa_adi}")
            
            # Calculate current balance for this register
            gelir = GenelKasaHareketi.objects.filter(kasa=kasa, hareket_tipi='Gelir').aggregate(toplam=Sum('tutar'))['toplam'] or 0
            gider = GenelKasaHareketi.objects.filter(kasa=kasa, hareket_tipi='Gider').aggregate(toplam=Sum('tutar'))['toplam'] or 0
            fatura = FaturaOdeme.objects.filter(Kasa=kasa).aggregate(toplam=Sum('Tutar'))['toplam'] or 0
            masraf = SeferMasraf.objects.filter(Kasa=kasa).aggregate(toplam=Sum('TutarEUR'))['toplam'] or 0
            
            guncel_bakiye = kasa.baslangic_bakiyesi + gelir - gider + fatura - masraf
            print(f"Current balance: {guncel_bakiye}")
            
            # Check if cash register has enough balance for expense
            if hareket_tipi == 'Gider' and guncel_bakiye < tutar:
                messages.error(
                    request, 
                    f"Yetersiz bakiye! {kasa.kasa_adi} kasasında {guncel_bakiye} {kasa.para_birimi} var."
                )
                print("Error: Insufficient balance")
                return render(request, 'sefer_app/genel_hareket_form.html', {'kasalar': kasalar})
            
            # Generate document number if none provided
            if not belge_no:
                belge_no = generate_kasa_belge_no()
                print(f"Generated document number: {belge_no}")
            
            # Create transaction
            hareket = GenelKasaHareketi.objects.create(
                kasa=kasa,
                hareket_tipi=hareket_tipi,
                kategori=kategori,
                gider_turu=gider_turu if hareket_tipi == 'Gider' else '',
                tutar=tutar,
                tarih=tarih or timezone.now(),
                belge_no=belge_no,
                aciklama=aciklama
            )
            print(f"Created transaction: {hareket.id}")
            
            messages.success(
                request, 
                f"{tutar} {kasa.para_birimi} tutarında {hareket_tipi.lower()} kaydı başarıyla oluşturuldu."
            )
            return redirect('kasa_detail', pk=kasa.id)
            
        except Exception as e:
            messages.error(request, f'İşlem hatası: {str(e)}')
            print(f"Exception occurred: {str(e)}")
            traceback.print_exc()
    
    context = {
        'kasalar': kasalar, 
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/genel_hareket_form.html', context)


def genel_hareket_update(request, pk):
    """Update an existing general transaction."""
    hareket = get_object_or_404(GenelKasaHareketi, pk=pk)
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    if request.method == 'POST':
        try:
            kasa_id = request.POST.get('kasa')
            hareket_tipi = request.POST.get('hareket_tipi')
            kategori = request.POST.get('kategori', '')
            gider_turu = request.POST.get('gider_turu', '')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            tarih = request.POST.get('tarih')
            belge_no = request.POST.get('belge_no', '')
            aciklama = request.POST.get('aciklama', '')
            
            # Generate document number if none provided and original had none
            if not belge_no and not hareket.belge_no:
                belge_no = generate_kasa_belge_no()
            
            if not kasa_id or not hareket_tipi:
                messages.error(request, 'Kasa ve hareket tipi seçimi zorunludur.')
                return render(request, 'sefer_app/genel_hareket_form.html', {'kasalar': kasalar, 'hareket': hareket})
                
            if tutar <= 0:
                messages.error(request, 'Tutar pozitif olmalıdır.')
                return render(request, 'sefer_app/genel_hareket_form.html', {'kasalar': kasalar, 'hareket': hareket})
            
            # Get cash register
            kasa = Kasalar.objects.get(id=kasa_id)
            
            # Update transaction
            hareket.kasa = kasa
            hareket.hareket_tipi = hareket_tipi
            hareket.kategori = kategori
            hareket.gider_turu = gider_turu if hareket_tipi == 'Gider' else ''
            hareket.tutar = tutar
            hareket.tarih = tarih or timezone.now()
            hareket.belge_no = belge_no
            hareket.aciklama = aciklama
            hareket.save()
            
            messages.success(
                request, 
                f"Kasa hareketi başarıyla güncellendi."
            )
            return redirect('kasa_detail', pk=kasa.id)
            
        except Exception as e:
            messages.error(request, f'İşlem hatası: {str(e)}')
    
    context = {
        'kasalar': kasalar,
        'hareket': hareket,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/genel_hareket_form.html', context)


def genel_hareket_delete(request, pk):
    """Delete a general transaction."""
    hareket = get_object_or_404(GenelKasaHareketi, pk=pk)
    kasa_id = hareket.kasa.id
    
    if request.method == 'POST':
        try:
            hareket.delete()
            messages.success(request, "Kasa hareketi başarıyla silindi.")
        except Exception as e:
            messages.error(request, f'İşlem hatası: {str(e)}')
            
    return redirect('kasa_detail', pk=kasa_id) 


def get_live_exchange_rate_ajax(request):
    from_currency_param = request.GET.get('from_currency')
    to_currency_param = request.GET.get('to_currency')
    
    print(f"AJAX Call: Raw params from='{from_currency_param}', to='{to_currency_param}'")

    if not from_currency_param or not to_currency_param:
        return JsonResponse({'error': 'Kaynak ve hedef para birimi kodları gerekli.'}, status=400)

    from_currency_iso = _resolve_currency_iso_code(from_currency_param)
    to_currency_iso = _resolve_currency_iso_code(to_currency_param)

    print(f"AJAX Call: Resolved ISO codes from='{from_currency_iso}', to='{to_currency_iso}'")

    if from_currency_iso == "XXX" or to_currency_iso == "XXX":
        # Corrected f-string for this block
        error_msg = f"Geçersiz para birimi kodu. Kaynak: {from_currency_param} (çözümlendi: {from_currency_iso}), Hedef: {to_currency_param} (çözümlendi: {to_currency_iso})"
        return JsonResponse({'error': error_msg}, status=400)

    if from_currency_iso == to_currency_iso:
        return JsonResponse({'rate': '1.000000'})

    rate_value = get_exchange_rate(from_currency_iso, to_currency_iso)

    if rate_value is None:
        print(f"AJAX Call: get_exchange_rate returned None for {from_currency_iso} -> {to_currency_iso}")
        # Corrected f-string for THIS block, which matches the traceback's problematic content
        error_msg = f"{from_currency_iso} -> {to_currency_iso} için kur bilgisi API'den alınamadı."
        return JsonResponse({'error': error_msg}, status=500)

    # Ensure rate_value is Decimal before quantize
    if not isinstance(rate_value, Decimal):
        print(f"AJAX Call: CRITICAL ERROR - get_exchange_rate non-Decimal/non-None bir değer döndürdü. Tip: {type(rate_value)}, Değer: {rate_value}")
        return JsonResponse({'error': 'Kur değeri işlenirken iç sunucu hatası (tip uyumsuzluğu).'}, status=500)

    try:
        quantizer = Decimal('0.000001')
        quantized_rate = rate_value.quantize(quantizer)
        quantized_rate_str = str(quantized_rate)
        return JsonResponse({'rate': quantized_rate_str})
    except Exception as e: 
        print(f"AJAX Call: ERROR quantizing rate. Değer: {rate_value}, Tip: {type(rate_value)}. Hata: {e}")
        traceback.print_exc()
        return JsonResponse({'error': 'Kur değeri işlenirken bir hata oluştu.'}, status=500) 
