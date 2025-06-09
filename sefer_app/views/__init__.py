"""
Views package for sefer_app.
This file imports all views from the individual modules.
"""

from . import arac_views
from . import sefer_views
from . import index_views
from . import masraf_views
# from . import bakim_views  # Artık mevcut değil, bu nedenle devre dışı bırakıldı
from . import firma_views
# from . import sofor_views  # Kontrol edilmeli, dosya mevcut olabilir
# from . import yakit_views  # Artık mevcut değil, bu nedenle devre dışı bırakıldı
from . import auth_views
from .fatura_views import *
from .kasa_views import *
from .personel_views import *
from .backup_views import * 
