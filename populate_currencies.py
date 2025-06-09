#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextsefer.settings')
django.setup()

from sefer_app.models import ParaBirimleri

# Define the currencies
currencies = [
    {'kod': 'EUR', 'ad': 'Euro', 'sembol': '€'},
    {'kod': 'CZK', 'ad': 'Çek Korunası', 'sembol': 'Kč'},
    {'kod': 'DKK', 'ad': 'Danimarka Kronu', 'sembol': 'kr'},
    {'kod': 'HUF', 'ad': 'Macar Forinti', 'sembol': 'Ft'},
    {'kod': 'NOK', 'ad': 'Norveç Kronu', 'sembol': 'kr'},
    {'kod': 'PLN', 'ad': 'Polonya Zlotisi', 'sembol': 'zł'},
    {'kod': 'SEK', 'ad': 'İsveç Kronu', 'sembol': 'kr'},
    {'kod': 'CHF', 'ad': 'İsviçre Frangı', 'sembol': 'Fr'},
    {'kod': 'ISK', 'ad': 'İzlanda Kronu', 'sembol': 'kr'},
    {'kod': 'RON', 'ad': 'Rumen Leyi', 'sembol': 'lei'},
    {'kod': 'BGN', 'ad': 'Bulgar Levi', 'sembol': 'лв'},
    {'kod': 'TRY', 'ad': 'Türk Lirası', 'sembol': '₺'},
]

# Add currencies to the database if they don't exist
for currency in currencies:
    ParaBirimleri.objects.get_or_create(
        kod=currency['kod'],
        defaults={
            'ad': currency['ad'],
            'sembol': currency['sembol'],
            'aktif': True
        }
    )

print(f"{len(currencies)} para birimi kontrol edildi ve eksik olanlar eklendi.") 