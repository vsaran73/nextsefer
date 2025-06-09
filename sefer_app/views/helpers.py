"""
Common helper functions for views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import os
from django.conf import settings

from ..models import Sehirler

# Common function for safely converting values to Decimal
def safe_decimal(value, default=Decimal('0.00')):
    """Convert a string to Decimal safely, with fallback to default."""
    if not value:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default

def format_decimal(value, decimal_places=2):
    """Format a decimal number with given decimal places."""
    if not isinstance(value, Decimal):
        if value is None:
            return "0,00"
        try:
            value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return "0,00"
    
    # Format with thousands separator and comma for decimal point
    quantized = value.quantize(Decimal('0.01'))
    
    # Convert to string and replace decimal point with comma for Turkish format
    formatted = str(quantized)
    
    # Ensure we don't output scientific notation
    if 'E' in formatted:
        # Convert scientific notation to standard format
        num = float(quantized)
        formatted = f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        # Standard decimal format, just replace dot with comma for Turkish format
        parts = formatted.split('.')
        if len(parts) == 2:
            int_part, decimal_part = parts
            if len(decimal_part) < decimal_places:
                decimal_part = decimal_part.ljust(decimal_places, '0')
            # Add thousands separator
            if len(int_part) > 3:
                int_part = '.'.join([int_part[max(0, i-3):i] for i in range(len(int_part), 0, -3)][::-1])
            formatted = f"{int_part},{decimal_part}"
        else:
            formatted = f"{formatted},{'0' * decimal_places}"
    
    return formatted

def format_currency(value, currency_code='EUR', decimal_places=2):
    """Format a number as currency with symbol."""
    if value is None:
        value = 0
    
    # Convert to float first if we have a Decimal to handle scientific notation properly
    if isinstance(value, Decimal) and 'E' in str(value):
        value = float(value)
    
    # Format numbers properly
    if isinstance(value, (int, float)):
        num_format = f"{value:,.{decimal_places}f}"
        # Convert to Turkish number format (1.234,56)
        formatted_value = num_format.replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        # Use format_decimal for other cases
        formatted_value = format_decimal(value, decimal_places)
    
    # Get currency symbol
    currency_symbols = {
        'EUR': '€',
        'USD': '$',
        'TRY': '₺',
        'GBP': '£'
    }
    
    symbol = currency_symbols.get(currency_code, currency_code)
    
    # Format with symbol (symbol at the end for EUR style)
    if currency_code in ['EUR', 'TRY']:
        return f"{formatted_value} {symbol}"
    else:
        return f"{symbol}{formatted_value}"

def clean_phone_number(phone_number):
    """Clean a phone number by removing non-digit characters."""
    if not phone_number:
        return ""
    return re.sub(r'\D', '', phone_number)

def register_ttf_fonts():
    """Register TTF fonts for ReportLab to enable proper Turkish character support"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os
    import sys
    
    # Try Windows system fonts first (most likely on this Windows system)
    try:
        # Register Arial - most common font with Turkish support
        system_root = os.environ.get('SYSTEMROOT', 'C:\\Windows')
        fonts_dir = os.path.join(system_root, 'Fonts')
        
        # First try to register Arial
        arial_path = os.path.join(fonts_dir, 'arial.ttf')
        arial_bold_path = os.path.join(fonts_dir, 'arialbd.ttf')
        arial_italic_path = os.path.join(fonts_dir, 'ariali.ttf')
        arial_bold_italic_path = os.path.join(fonts_dir, 'arialbi.ttf')
        
        if os.path.exists(arial_path):
            # Register all Arial variants
            pdfmetrics.registerFont(TTFont('Arial', arial_path))
            if os.path.exists(arial_bold_path):
                pdfmetrics.registerFont(TTFont('Arial-Bold', arial_bold_path))
            if os.path.exists(arial_italic_path):
                pdfmetrics.registerFont(TTFont('Arial-Italic', arial_italic_path))
            if os.path.exists(arial_bold_italic_path):
                pdfmetrics.registerFont(TTFont('Arial-BoldItalic', arial_bold_italic_path))
                
            # Create a font family for proper bold/italic handling
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', 
                             italic='Arial-Italic', boldItalic='Arial-BoldItalic')
            return 'Arial'
            
        # If Arial isn't available, try these other common fonts
        common_fonts = [
            ('calibri.ttf', 'calibrib.ttf', 'calibrii.ttf', 'calibriz.ttf', 'Calibri'),
            ('segoeui.ttf', 'segoeuib.ttf', 'segoeuii.ttf', 'segoeuiz.ttf', 'Segoe UI'),
            ('verdana.ttf', 'verdanab.ttf', 'verdanai.ttf', 'verdanaz.ttf', 'Verdana'),
            ('tahoma.ttf', 'tahomabd.ttf', None, None, 'Tahoma'),
        ]
        
        for regular, bold, italic, bolditalic, family in common_fonts:
            regular_path = os.path.join(fonts_dir, regular)
            if os.path.exists(regular_path):
                pdfmetrics.registerFont(TTFont(family, regular_path))
                
                # Register variants if they exist
                if bold and os.path.exists(os.path.join(fonts_dir, bold)):
                    pdfmetrics.registerFont(TTFont(f'{family}-Bold', os.path.join(fonts_dir, bold)))
                if italic and os.path.exists(os.path.join(fonts_dir, italic)):
                    pdfmetrics.registerFont(TTFont(f'{family}-Italic', os.path.join(fonts_dir, italic)))
                if bolditalic and os.path.exists(os.path.join(fonts_dir, bolditalic)):
                    pdfmetrics.registerFont(TTFont(f'{family}-BoldItalic', os.path.join(fonts_dir, bolditalic)))
                
                # Create font family
                variants = {
                    'normal': family,
                    'bold': f'{family}-Bold' if bold and os.path.exists(os.path.join(fonts_dir, bold)) else family,
                    'italic': f'{family}-Italic' if italic and os.path.exists(os.path.join(fonts_dir, italic)) else family,
                    'boldItalic': f'{family}-BoldItalic' if bolditalic and os.path.exists(os.path.join(fonts_dir, bolditalic)) else family
                }
                
                try:
                    registerFontFamily(family, **variants)
                except:
                    pass
                
                return family
    except Exception as e:
        print(f"Error registering system fonts: {e}")
    
    # Return Helvetica as fallback if nothing else works
    return 'Helvetica'

# Function to handle Turkish characters in PDF text without relying on fonts
def turkish_safe_text(text):
    """Process text to safely display Turkish characters in PDFs even with standard fonts"""
    if not text:
        return ""
    
    # Create a mapping for Turkish characters to their closest ASCII equivalents
    tr_map = {
        'ç': 'c', 'Ç': 'C',
        'ğ': 'g', 'Ğ': 'G',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O',
        'ş': 's', 'Ş': 'S',
        'ü': 'u', 'Ü': 'U',
    }
    
    # Apply the mapping only when a font without Turkish support is used
    result = ""
    for char in text:
        result += tr_map.get(char, char)
    
    return result

# Define constants for option choices
MASRAF_TIPLERI = [
    'Yakıt',
    'Yol Ücreti',
    'Konaklama',
    'Yemek',
    'Araç Bakım',
    'Ruhsat/Belge',
    'Park Ücreti',
    'Ceza',
    'Diğer'
] 

def get_cities_by_country(request):
    """API endpoint to get cities by country."""
    country_id = request.GET.get('country_id')
    if not country_id:
        return JsonResponse({'cities': []})
        
    cities = Sehirler.objects.filter(ulke_id=country_id).values('id', 'sehir_adi')
    return JsonResponse({'cities': list(cities)})

def get_first_two_words(text):
    """
    Verilen metindeki ilk iki kelimeyi alır.
    Eğer metin iki kelimeden azsa, metnin tamamını döndürür.
    """
    if text is None:
        return ""
        
    words = str(text).split()
    if len(words) <= 2:
        return text
    return " ".join(words[:2]) 
    return JsonResponse({'cities': list(cities)}) 