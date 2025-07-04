# Generated by Django 5.2.1 on 2025-06-03 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sefer_app', '0009_aracuyari_bildirim_turu_aracuyari_hatirlatici_gun_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aracuyari',
            name='durum',
            field=models.CharField(choices=[('aktif', 'Aktif'), ('tamamlandi', 'Tamamlandı'), ('ertelendi', 'Ertelendi'), ('iptal', 'İptal')], default='aktif', max_length=50),
        ),
        migrations.AlterField(
            model_name='aracuyari',
            name='oncelik',
            field=models.CharField(choices=[('dusuk', 'Düşük'), ('orta', 'Normal'), ('yuksek', 'Yüksek')], default='orta', max_length=20),
        ),
        migrations.AlterField(
            model_name='aracuyari',
            name='uyari_turu',
            field=models.CharField(choices=[('muayene', 'Muayene'), ('sigorta', 'Sigorta'), ('bakim', 'Bakım'), ('vergi', 'Vergi'), ('lastik', 'Lastik Değişimi'), ('yag', 'Yağ Değişimi'), ('belge', 'Belge Yenileme'), ('diger', 'Diğer')], default='bakim', max_length=100),
        ),
    ]
