#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django
import logging

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def setup_django():
    """Django ayarlarını yükle"""
    try:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nextsefer.settings")
        django.setup()
        logger.info("Django ayarları yüklendi.")
    except Exception as e:
        logger.error(f"Django ayarları yüklenirken hata: {e}")
        sys.exit(1)

def create_admin_user():
    """Admin kullanıcısı oluştur"""
    from django.contrib.auth.models import User
    
    try:
        username = 'admin'
        password = 'admin'
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username, 
                email='admin@example.com', 
                password=password
            )
            logger.info(f"Admin kullanıcısı oluşturuldu: {username}")
        else:
            logger.info("Admin kullanıcısı zaten mevcut.")
            
        return True
    except Exception as e:
        logger.error(f"Admin kullanıcısı oluşturulurken hata: {e}")
        return False

def main():
    """Ana fonksiyon"""
    setup_django()
    if create_admin_user():
        logger.info("Admin kullanıcısı hazır.")
        print("Admin kullanıcısı oluşturuldu/kontrol edildi!")
        print("Kullanıcı adı: admin")
        print("Şifre: admin")
    else:
        logger.error("Admin kullanıcısı oluşturulamadı!")

if __name__ == "__main__":
    main() 
 
 
 