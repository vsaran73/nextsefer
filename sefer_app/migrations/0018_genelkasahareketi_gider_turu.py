# Generated by Django 5.2.1 on 2025-06-04 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sefer_app', '0017_personelodeme'),
    ]

    operations = [
        migrations.AddField(
            model_name='genelkasahareketi',
            name='gider_turu',
            field=models.CharField(blank=True, choices=[('', '-'), ('Sabit', 'Sabit Gider'), ('Değişken', 'Değişken Gider'), ('Beklenmeyen', 'Beklenmeyen Gider'), ('Operasyonel', 'Operasyonel Gider'), ('Yatırım', 'Yatırım'), ('Diğer', 'Diğer')], default='', max_length=20),
        ),
    ]
