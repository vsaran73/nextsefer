"""
Dashboard and main index views.
"""

from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce, TruncMonth, TruncDate, TruncDay
from django.db.models import DecimalField
from datetime import datetime, timedelta
import calendar
import json

from ..models import Seferler, Faturalar, SeferMasraf, AracUyari, FirmaBilgi
from ..forms import FirmaBilgiForm, KullaniciKurulumForm

def firma_bilgi_kurulum(request):
    """İlk kurulumda firma ve admin kullanıcı formu"""
    from django.contrib.auth.models import User
    from django.contrib.auth.decorators import login_required
    if not request.user.is_authenticated:
        return redirect('login')
    if FirmaBilgi.objects.exists():
        return redirect('index')
    if request.method == 'POST':
        firma_form = FirmaBilgiForm(request.POST)
        kullanici_form = KullaniciKurulumForm(request.POST)
        if firma_form.is_valid() and kullanici_form.is_valid():
            firma_form.save()
            user = kullanici_form.save(commit=False)
            user.set_password(kullanici_form.cleaned_data['password1'])
            user.is_superuser = True
            user.is_staff = True
            user.save()
            messages.success(request, 'Kurulum tamamlandı! Giriş yapabilirsiniz.')
            return redirect('index')
    else:
        firma_form = FirmaBilgiForm()
        kullanici_form = KullaniciKurulumForm()
    return render(request, 'kurulum/firma_bilgi_kurulum.html', {'firma_form': firma_form, 'kullanici_form': kullanici_form})

def index(request):
    """Dashboard view showing overview of trips, income, expenses, and alerts."""
    # Firma bilgisi yoksa kurulum sayfasına yönlendir
    if not FirmaBilgi.objects.exists():
        return redirect('firma_bilgi_kurulum')
    
    # Get filter period (default to current month)
    filter_period = request.GET.get('period', 'month')
    
    today = timezone.now().date()
    current_year = today.year
    
    # Set date ranges based on filter period
    if filter_period == 'month':
        # Current month
        start_date = today.replace(
            day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(
            day=last_day)
        period_name = f"{today.year}-{today.month:02d} Ayı"
        chart_trunc = TruncDay
        chart_labels = [str(i) for i in range(1, last_day + 1)]  # Days in current month
    elif filter_period == '30days':
        # Last 30 days
        start_date = today - timedelta(days=30)
        end_date = today
        period_name = "Son 30 Gün"
        chart_trunc = TruncDay
        # Generate date labels for the last 30 days
        chart_labels = [(today - timedelta(days=i)).strftime('%d-%m') for i in range(30, -1, -1)]
    elif filter_period == 'year':
        # Current year
        start_date = today.replace(
            month=1,
            day=1)
        end_date = today.replace(
            month=12,
            day=31)
        period_name = str(today.year)
        chart_trunc = TruncMonth
        chart_labels = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
    else:  # 'all'
        # All time
        start_date = datetime(1900, 1, 1).date()
        end_date = datetime(2100, 12, 31).date()
        period_name = "Tümü"
        chart_trunc = TruncMonth
        chart_labels = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
    
    # Count trips for the selected period
    if filter_period == 'all':
        # Count all trips regardless of date for 'all' filter
        sefer_sayisi = Seferler.objects.count()
    else:
        # Count trips within the date range for other filters
        sefer_sayisi = Seferler.objects.filter(
            Q(cikis_tarihi__range=(start_date, end_date)) | 
            Q(varis_tarihi__range=(start_date, end_date))
        ).count()
    
    # Calculate total income (from faturalar)
    faturalar = Faturalar.objects.filter(
        FaturaTarihi__range=(
            start_date, end_date), FaturaTipi__in=[
            'Satış', 'Nakliye'])
    gelir = faturalar.aggregate(total=Coalesce(Sum('ToplamTutar'), 0, output_field=DecimalField()))['total'] or 0
    
    # Calculate total expenses (from masraflar)
    masraflar = SeferMasraf.objects.filter(Tarih__range=(start_date, end_date))
    gider = masraflar.aggregate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField()))['total'] or 0
    
    # Get active alerts
    uyari_sayisi = AracUyari.objects.filter(durum='aktif').count()
    
    # Get active trips for display
    aktif_seferler = Seferler.objects.filter(durum='Aktif').order_by('-cikis_tarihi')[:5]
    
    # Get active alerts for display, sorted by priority and deadline
    aktif_uyarilar = AracUyari.objects.filter(durum='aktif').order_by('-oncelik', 'son_tarih')[:5]
    
    # Get upcoming receivables (Yakındaki Alacaklar)
    # These are unpaid or partially paid invoices of type 'Satış' or 'Nakliye' with upcoming due dates
    yakindaki_alacaklar = Faturalar.objects.filter(
        FaturaTipi__in=['Satış', 'Nakliye'],
        OdemeDurumu__in=['Ödenmedi', 'Kısmi Ödeme']
    ).annotate(
        kalan_tutar=F('ToplamTutar') - F('OdenenTutar')
    ).order_by('VadeTarihi')[:5]
    
    # Get upcoming payments (Yakındaki Ödemeler)
    # These are unpaid or partially paid invoices of type 'Alış' with upcoming due dates
    yakindaki_odemeler = Faturalar.objects.filter(
        FaturaTipi='Alış',
        OdemeDurumu__in=['Ödenmedi', 'Kısmi Ödeme']
    ).annotate(
        kalan_tutar=F('ToplamTutar') - F('OdenenTutar')
    ).order_by('VadeTarihi')[:5]
    
    # Prepare data for charts
    
    # Adjust chart data based on selected period
    if filter_period == 'month':
        # Daily income/expense for current month
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        income_data = [0] * days_in_month
        expense_data = [0] * days_in_month

        # Get daily income
        daily_income = (Faturalar.objects
                        .filter(FaturaTarihi__year=today.year, FaturaTarihi__month=today.month, FaturaTipi__in=['Satış', 'Nakliye'])
                        .annotate(day=TruncDay('FaturaTarihi'))
                        .values('day')
                        .annotate(total=Coalesce(Sum('ToplamTutar'), 0, output_field=DecimalField()))
                        .order_by('day'))

        # Get daily expenses
        daily_expense = (SeferMasraf.objects
                        .filter(Tarih__year=today.year, Tarih__month=today.month)
                        .annotate(day=TruncDay('Tarih'))
                        .values('day')
                        .annotate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField()))
                        .order_by('day'))

        # Fill in daily data
        for item in daily_income:
            if item['day'] and item['day'].day >= 1 and item['day'].day <= days_in_month:
                income_data[item['day'].day - 1] = float(item['total'])

        for item in daily_expense:
            if item['day'] and item['day'].day >= 1 and item['day'].day <= days_in_month:
                expense_data[item['day'].day - 1] = float(item['total'])

    elif filter_period == '30days':
        # Last 30 days data
        income_data = [0] * 31  # Today + last 30 days
        expense_data = [0] * 31  
        
        # Date range for last 30 days
        thirty_days_ago = today - timedelta(days=30)
        
        # Get daily income for last 30 days
        daily_income = (Faturalar.objects
                        .filter(FaturaTarihi__gte=thirty_days_ago, FaturaTarihi__lte=today, FaturaTipi__in=['Satış', 'Nakliye'])
                        .annotate(day=TruncDay('FaturaTarihi'))
                        .values('day')
                        .annotate(total=Coalesce(Sum('ToplamTutar'), 0, output_field=DecimalField())))
        
        # Get daily expenses for last 30 days
        daily_expense = (SeferMasraf.objects
                        .filter(Tarih__gte=thirty_days_ago, Tarih__lte=today)
                        .annotate(day=TruncDay('Tarih'))
                        .values('day')
                        .annotate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField())))
        
        # Process data for last 30 days
        for i in range(31):  # 0 to 30
            current_date = today - timedelta(days=30-i)
            # Find matching income
            for income in daily_income:
                if income['day'] and (income['day'] == current_date or 
                   (hasattr(income['day'], 'date') and income['day'].date() == current_date)):
                    income_data[i] = float(income['total'])
                    break
            # Find matching expense
            for expense in daily_expense:
                if expense['day'] and (expense['day'] == current_date or 
                   (hasattr(expense['day'], 'date') and expense['day'].date() == current_date)):
                    expense_data[i] = float(expense['total'])
                    break
    else:
        # Year or all-time view (monthly data)
        income_data = [0] * 12  # Initialize with zeros
        expense_data = [0] * 12  # Initialize with zeros

        query_filter = {}
        if filter_period == 'year':
            query_filter = {'FaturaTarihi__year': current_year}
            expense_filter = {'Tarih__year': current_year}
        else:
            query_filter = {}
            expense_filter = {}
        
        # Get monthly income
        monthly_income = (Faturalar.objects
                        .filter(FaturaTipi__in=['Satış', 'Nakliye'], **query_filter)
                        .annotate(month=TruncMonth('FaturaTarihi'))
                        .values('month')
                        .annotate(total=Coalesce(Sum('ToplamTutar'), 0, output_field=DecimalField()))
                        .order_by('month'))

        # Get monthly expenses
        monthly_expense = (SeferMasraf.objects
                        .filter(**expense_filter)
                        .annotate(month=TruncMonth('Tarih'))
                        .values('month')
                        .annotate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField()))
                        .order_by('month'))
        
        # Fill in data from database (limited to current year for display)
        current_year = today.year
        for item in monthly_income:
            if item['month'] and item['month'].year == current_year and 1 <= item['month'].month <= 12:
                income_data[item['month'].month - 1] = float(item['total'])
        
        for item in monthly_expense:
            if item['month'] and item['month'].year == current_year and 1 <= item['month'].month <= 12:
                expense_data[item['month'].month - 1] = float(item['total'])
    
    # Expense distribution by type (pie chart)
    expense_types = (SeferMasraf.objects
                    .filter(Tarih__range=(start_date, end_date))
                    .values('MasrafTipi')
                    .annotate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField()))
                    .order_by('-total'))
    
    expense_categories = []
    expense_values = []
    expense_colors = [
        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', 
        '#fd7e14', '#6f42c1', '#20c9a6', '#5a5c69', '#858796'
    ]
    
    for idx, expense in enumerate(expense_types):
        if idx < 10:  # Limit to top 10 expense types
            expense_categories.append(expense['MasrafTipi'] or 'Diğer')
            expense_values.append(float(expense['total']))
    
    # Ensure we have enough colors
    while len(expense_colors) < len(expense_categories):
        expense_colors.extend(expense_colors[:len(expense_categories)-len(expense_colors)])
    
    context = {
        'filter_period': filter_period,
        'period_name': period_name,
        'sefer_sayisi': sefer_sayisi,
        'gelir': gelir,
        'gider': gider,  # Converting to float as needed
        'uyari_sayisi': uyari_sayisi,
        'aktif_seferler': aktif_seferler,
        'aktif_uyarilar': aktif_uyarilar,
        'yakindaki_alacaklar': yakindaki_alacaklar,
        'yakindaki_odemeler': yakindaki_odemeler,
        'today': today,  # Bugünün tarihini template'e gönderiyoruz
        # Chart data
        'income_data': json.dumps(income_data),
        'expense_data': json.dumps(expense_data),
        'months': json.dumps(chart_labels),
        'expense_categories': json.dumps(expense_categories),
        'expense_values': json.dumps(expense_values),
        'expense_colors': json.dumps(expense_colors[:len(expense_categories)])
    }
    return render(request, 'sefer_app/index.html', context) 