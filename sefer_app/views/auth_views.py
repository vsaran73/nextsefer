from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
import logging
from sefer_app.models import FirmaBilgi

logger = logging.getLogger(__name__)

def register_admin_view(request):
    # Eğer sistemde kullanıcı varsa, login sayfasına yönlendir
    if User.objects.exists():
        return redirect('login')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        if not username or not password:
            error = 'Kullanıcı adı ve şifre zorunludur.'
        elif User.objects.filter(username=username).exists():
            error = 'Bu kullanıcı adı zaten mevcut.'
        else:
            user = User.objects.create_superuser(username=username, email=email or '', password=password)
            login(request, user)
            # Firma bilgisi kontrolü
            firma_bilgi = FirmaBilgi.objects.first()
            if not firma_bilgi or not firma_bilgi.unvan or not firma_bilgi.adres or not firma_bilgi.telefon:
                return redirect('/firma_bilgi_kurulum/')
            return redirect('index')
    return render(request, 'register_admin.html', {'error': error})

def login_view(request):
    """
    Login view that handles user authentication.
    """
    error = None

    # Eğer hiç kullanıcı yoksa, admin kayıt ekranına yönlendir
    if not User.objects.exists():
        return redirect('register_admin')

    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # FirmaBilgi kontrolü
            firma_bilgi = FirmaBilgi.objects.first()
            if not firma_bilgi or not firma_bilgi.unvan or not firma_bilgi.adres or not firma_bilgi.telefon:
                return redirect('/firma_bilgi_kurulum/')
            return redirect('index')
        else:
            error = "Invalid credentials"

    return render(request, 'login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

def auto_login(request):
    """Otomatik login yapıp anasayfaya yönlendir"""
    try:
        # Varsayılan bir kullanıcı varsa veya oluştur
        username = 'admin'
        password = 'admin'
        
        # Kullanıcı yoksa oluştur
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email='admin@example.com', password=password)
            logger.info(f"Created default user: {username}")
        
        # Otomatik login
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            logger.info(f"Auto-login successful for user: {username}")
    except Exception as e:
        logger.error(f"Auto-login error: {e}")
    
    return redirect('index')

def check_admin_user():
    """Admin kullanıcısı kontrolü, yoksa oluştur"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@nextsefer.com',
            password='nextsefer2023'
        )
        logger.info("Admin kullanıcısı oluşturuldu") 
 
 