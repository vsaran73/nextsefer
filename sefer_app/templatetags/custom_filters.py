from django import template
from decimal import Decimal
from django.utils.safestring import mark_safe
import datetime

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def comma_format(value):
    """Format number with comma as decimal separator."""
    try:
        # Convert to Decimal for better precision than float
        if isinstance(value, str):
            value = value.replace(',', '.')
        value_decimal = Decimal(str(value))
        # Format with 2 decimal places and replace period with comma
        formatted = '{:.2f}'.format(value_decimal).replace('.', ',')
        print(f"comma_format: input={value}, decimal={value_decimal}, output={formatted}")
        return formatted
    except (ValueError, TypeError) as e:
        print(f"comma_format error: {e} on value {value}")
        return value
        
@register.simple_tag
def calculate_total_expense(sefer_masraf, genel_gider, fatura_odeme, giden_transfer):
    """Calculate total expense and format with comma decimal separator."""
    try:
        # Convert all inputs to Decimal for accurate calculation
        sm = Decimal('0') if sefer_masraf is None else Decimal(str(sefer_masraf))
        gg = Decimal('0') if genel_gider is None else Decimal(str(genel_gider))
        fo = Decimal('0') if fatura_odeme is None else Decimal(str(fatura_odeme))
        gt = Decimal('0') if giden_transfer is None else Decimal(str(giden_transfer))
        
        # Calculate total
        total = sm + gg + fo + gt
        
        # Format with 2 decimal places and comma as separator
        formatted = '{:.2f}'.format(total).replace('.', ',')
        print(f"Total expense calculation: {sm} + {gg} + {fo} + {gt} = {total} → {formatted}")
        return formatted
    except Exception as e:
        print(f"Total expense calculation error: {e}")
        return "0,00"

@register.filter(name='abs_value')
def abs_value(value):
    """Return the absolute value of a number."""
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value

@register.filter
def oncelik_sinifi(oncelik):
    """Return the appropriate CSS class based on priority level."""
    if oncelik == 'yuksek':
        return 'urgent'
    elif oncelik == 'orta':
        return 'warning'
    else:  # 'dusuk' or any other value
        return 'normal'

@register.filter
def days_until(value):
    """Return the number of days between today and a given date."""
    if not value:
        return None
    
    today = datetime.date.today()
    try:
        if isinstance(value, datetime.datetime):
            value_date = value.date()
        else:
            value_date = value
            
        return (value_date - today).days
    except (ValueError, TypeError, AttributeError):
        return None

@register.filter
def due_date_color(days):
    """Return the appropriate text color based on days until due date."""
    if days is None:
        return ''
    
    if days < 0:  # Overdue
        return 'text-danger'
    else:  # Due in the future
        return 'text-success'

@register.filter
def group_thousands(value, separator='.'):
    """
    Adds thousand separators to a number.
    Example: 1234567 becomes 1.234.567 with default separator
    """
    try:
        # Remove any spaces
        value = str(value).strip()
        
        # Check if empty or too small
        if not value or value == '0':
            return '0'
            
        # Skip adding thousands separators for numbers less than 1000
        if len(value) <= 3:
            return value
            
        # Process the number by adding separators
        result = ''
        for i, digit in enumerate(reversed(value)):
            if i > 0 and i % 3 == 0:
                result = separator + result
            result = digit + result
        return result
    except (ValueError, TypeError):
        return value

@register.filter
def is_negative(value):
    """
    Check if a value is negative.
    Returns True if value is negative, False otherwise.
    """
    try:
        return str(value).startswith('-')
    except:
        return False
        
@register.filter
def format_number(value, use_thousands=True):
    """
    Formats a number with comma as decimal separator and dots for thousands.
    Handles negative values correctly.
    """
    try:
        value_str = str(value).strip()
        negative = value_str.startswith('-')
        
        # Remove negative sign for processing
        if negative:
            value_str = value_str[1:]
            
        # Split into whole and decimal parts
        parts = value_str.split('.')
        whole = parts[0]
        decimal = parts[1][:2] if len(parts) > 1 else '00'
        decimal = decimal.ljust(2, '0')
        
        # Apply thousands separator if needed and number is large enough
        if use_thousands and len(whole) > 3:
            result = ''
            for i, digit in enumerate(reversed(whole)):
                if i > 0 and i % 3 == 0:
                    result = '.' + result
                result = digit + result
            whole = result
            
        # Reassemble with comma as decimal separator
        formatted = whole + ',' + decimal
        
        # Add back negative sign if needed
        if negative:
            formatted = '-' + formatted
            
        return formatted
    except:
        return value

@register.filter
def currency_symbol(currency_code):
    """
    Returns the appropriate currency symbol for a given currency code.
    Example: 'USD' returns '$', 'EUR' returns '€'
    """
    CURRENCY_SYMBOLS = {
        'EUR': '€',
        'USD': '$',
        'TRY': '₺',
        'GBP': '£',
        'TL': '₺'  # Eski Türk Lirası kodu için de aynı sembol
    }
    
    # First try to normalize the code (handle case variations)
    if currency_code:
        currency_code = str(currency_code).strip().upper()
    
    # Return the symbol if found, otherwise return the code itself
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)