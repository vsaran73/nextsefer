import re
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import User

class LoginRequiredMiddleware:
    """
    Tüm sayfaları giriş yapılması gereken sayfalar haline getirir.
    Belirtilen URL'ler hariç tüm sayfalar için giriş yapılması gerekir.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Public URL'ler - giriş yapmadan erişilebilecek
        self.public_urls = [
            re.compile(r'^/login/$'),
            re.compile(r'^/register_admin/$'),
            re.compile(r'^/admin/login/$'),
            re.compile(r'^/static/.*$'),
            re.compile(r'^/media/.*$'),
            re.compile(r'^/manifest\.json$'),
            re.compile(r'^/serviceworker\.js$'),
            re.compile(r'^/updates/check/$'),  # Otomatik güncelleme kontrolü
            # re.compile(r'^/firma_bilgi_kurulum/$'),  # Artık public değil!
        ]
    
    def __call__(self, request):
        # Geçerli URL
        path = request.path_info
        
        # Kullanıcı giriş yapmış mı?
        user = request.user
        
        # Public URL'lerden birine erişiliyor mu?
        is_public = any(url.match(path) for url in self.public_urls)
        
        # Eğer public URL değilse ve kullanıcı giriş yapmamışsa, giriş sayfasına yönlendir
        if not is_public and not user.is_authenticated:
            return redirect(f"/login/?next={path}")
        
        # --- Firma bilgisi kontrolü ---
        # Sadece giriş yapmış kullanıcılar ve public olmayan sayfalar için uygula
        if user.is_authenticated and not is_public:
            from sefer_app.models import FirmaBilgi
            firma_bilgi = FirmaBilgi.objects.first()
            # Firma bilgisi eksikse ve şu an firma_bilgi_kurulum sayfasında değilse yönlendir
            if (not firma_bilgi or not firma_bilgi.unvan or not firma_bilgi.adres or not firma_bilgi.telefon):
                if not path.startswith('/firma_bilgi_kurulum/'):
                    return redirect('/firma_bilgi_kurulum/')
        
        # Eğer hiç kullanıcı yoksa, register_admin sayfasına yönlendir
        if not User.objects.exists() and not any(url.match(path) for url in [re.compile(r'^/register_admin/$'), re.compile(r'^/static/.*$'), re.compile(r'^/media/.*$')]):
            return redirect('/register_admin/')
        
        # Diğer durumda normal işlem devam eder
        response = self.get_response(request)
        return response 
 
 