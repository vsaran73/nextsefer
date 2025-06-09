from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_default_admin(sender, **kwargs):
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')

class SeferAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sefer_app'

    def ready(self):
        # Import signals here if you have any
        # This ensures the app is fully loaded when Django starts
        post_migrate.connect(create_default_admin, sender=self)
