#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import traceback
import logging
import pprint

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("django_debug")

def main():
    """Django ayarlarını ve modüllerini kontrol et"""
    try:
        # Çalışma dizinini ayarla
        current_dir = os.path.abspath(os.path.dirname(__file__))
        sys.path.append(current_dir)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        os.environ["DEBUG"] = "True"

        # Çalışma dizinlerini göster
        logger.info(f"Çalışma dizini: {os.getcwd()}")
        logger.info(f"sys.path: {sys.path}")
        
        # Proje dosyalarını kontrol et
        project_files = [
            "manage.py",
            "db.sqlite3",
            "nextsefer/settings.py",
            "nextsefer/urls.py",
            "nextsefer/wsgi.py",
            "sefer_app/views.py",
            "sefer_app/models.py",
            "sefer_app/urls.py",
        ]
        
        for file_path in project_files:
            full_path = os.path.join(current_dir, file_path)
            if os.path.exists(full_path):
                logger.info(f"✓ {file_path} mevcut")
            else:
                logger.error(f"✗ {file_path} bulunamadı!")
        
        # Django'yu import et
        logger.info("Django modüllerini import ediliyor...")
        import django
        logger.info(f"Django sürümü: {django.__version__}")
        
        # Django ayarlarını yükle
        logger.info("Django ayarları yükleniyor...")
        django.setup()
        
        # Veritabanı ayarlarını kontrol et
        from django.conf import settings
        logger.info("Django ayarları yüklendi")
        
        logger.info("Veritabanı ayarları:")
        logger.info(pprint.pformat(settings.DATABASES))
        
        logger.info("Yüklü uygulamalar:")
        logger.info(pprint.pformat(settings.INSTALLED_APPS))
        
        # Modelleri kontrol et
        logger.info("Modeller kontrol ediliyor...")
        from django.apps import apps
        
        for app_config in apps.get_app_configs():
            logger.info(f"Uygulama: {app_config.name}")
            for model in app_config.get_models():
                logger.info(f"  Model: {model.__name__}")
        
        # URL yapılandırmasını kontrol et
        logger.info("URL yapılandırması kontrol ediliyor...")
        from django.urls import get_resolver
        resolver = get_resolver(None)
        patterns = resolver.url_patterns
        
        logger.info(f"Toplam URL pattern sayısı: {len(patterns)}")
        for pattern in patterns[:5]:  # İlk 5 pattern'i göster
            logger.info(f"  {pattern}")
        
        # Sunucuyu başlat
        logger.info("Web sunucusu başlatılıyor...")
        from django.core.management import call_command
        call_command('runserver', '8000')
        
    except ImportError as e:
        logger.error(f"Import hatası: {e}")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Hata: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 
 
 
 