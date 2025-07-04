# Generated by Django 5.2.1 on 2025-06-04 18:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sefer_app', '0016_remove_kilometre_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonelOdeme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('belge_no', models.CharField(max_length=15, unique=True)),
                ('tarih', models.DateField()),
                ('tutar', models.DecimalField(decimal_places=2, max_digits=10)),
                ('odeme_turu', models.CharField(choices=[('Maaş', 'Maaş'), ('Avans', 'Avans'), ('Harcırah', 'Harcırah'), ('Prim', 'Prim'), ('İkramiye', 'İkramiye'), ('Diğer', 'Diğer')], max_length=20)),
                ('aciklama', models.TextField(blank=True, null=True)),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True)),
                ('guncelleme_tarihi', models.DateTimeField(auto_now=True)),
                ('personel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='odemeler', to='sefer_app.personeller')),
            ],
            options={
                'verbose_name': 'Personel Ödemesi',
                'verbose_name_plural': 'Personel Ödemeleri',
                'ordering': ['-tarih', '-olusturulma_tarihi'],
            },
        ),
    ]
