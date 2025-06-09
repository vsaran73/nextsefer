import requests
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from .models import ParaBirimleri, FirmaBilgi

def get_exchange_rates():
    """
    Fetch current exchange rates from a public API.
    Returns a dictionary of currency codes and their rates relative to EUR.
    Caches results for 24 hours.
    """
    # Check if rates are in cache
    cached_rates = cache.get('exchange_rates')
    if cached_rates:
        return cached_rates
    
    # If not in cache, fetch new rates
    try:
        # Try the European Central Bank API (free, no key required)
        response = requests.get('https://open.er-api.com/v6/latest/EUR')
        data = response.json()
        
        if data and 'rates' in data:
            rates = data['rates']
            # Add EUR rate (1.0)
            rates['EUR'] = 1.0
            
            # Cache for 24 hours
            cache.set('exchange_rates', rates, 60 * 60 * 24)
            return rates
        else:
            raise Exception("No rates in API response")
    except Exception as e:
        # If API call fails, use fallback rates
        fallback_rates = {
            'EUR': 1.0,
            'TRY': 44.53,  # Updated rate
            'CZK': 24.92,
            'DKK': 7.46,
            'HUF': 403.84,
            'NOK': 11.57,
            'PLN': 4.25,
            'SEK': 10.89,
            'CHF': 0.93,
            'ISK': 144.20,
            'RON': 5.06,
            'BGN': 1.96,
        }
        cache.set('exchange_rates', fallback_rates, 60 * 60 * 6)  # Cache fallback for 6 hours
        return fallback_rates

def convert_currency(amount, from_currency, to_currency='EUR'):
    """
    Convert an amount from one currency to another.
    
    Args:
        amount: The amount to convert
        from_currency: Source currency code (e.g., 'USD')
        to_currency: Target currency code (default: 'EUR')
        
    Returns:
        tuple: (converted_amount, exchange_rate)
    """
    rates = get_exchange_rates()
    
    # If either currency is not in rates, return the original amount
    if from_currency not in rates or to_currency not in rates:
        return amount, 1.0
    
    # Calculate exchange rate (through EUR as base)
    if from_currency == to_currency:
        return amount, 1.0
    
    # If converting to EUR
    if to_currency == 'EUR':
        # The rate is how many units of from_currency equals 1 EUR
        rate = rates[from_currency]
        # So to get EUR, divide the amount by the rate
        converted_amount = amount / rate
        return converted_amount, rate
    
    # If converting from EUR
    if from_currency == 'EUR':
        # The rate is how many units of to_currency equals 1 EUR
        rate = rates[to_currency]
        # So multiply EUR by the rate
        converted_amount = amount * rate
        return converted_amount, rate
    
    # If converting between non-EUR currencies
    # First convert to EUR, then to target currency
    eur_amount = amount / rates[from_currency]
    converted_amount = eur_amount * rates[to_currency]
    
    # Calculate direct exchange rate
    exchange_rate = rates[to_currency] / rates[from_currency]
    
    return converted_amount, exchange_rate

def get_active_currencies():
    """
    Get all active currencies from the database.
    Returns a list of dictionaries with currency information.
    """
    currencies = ParaBirimleri.objects.filter(aktif=True).values('kod', 'ad', 'sembol')
    return list(currencies)

def get_firma_unvan():
    firma = FirmaBilgi.objects.first()
    if firma and firma.unvan:
        return firma.unvan
    return "Next Global Logistic" 