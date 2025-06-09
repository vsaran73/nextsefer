from django.core.management.base import BaseCommand
from django.db import connection
from sefer_app.models import Seferler, Faturalar
from decimal import Decimal

class Command(BaseCommand):
    help = 'Tüm nakliye faturalarının değerlerini ilgili seferlerin ücret değerlerine aktarır'

    def handle(self, *args, **options):
        # Django ORM kullanarak nakliye faturalarını al
        nakliye_faturalari = Faturalar.objects.filter(FaturaTipi='Nakliye', Sefer__isnull=False)
        self.stdout.write(f"Toplam {nakliye_faturalari.count()} adet nakliye faturası bulundu")
        
        # Her sefere ait nakliye faturalarının toplamını hesapla
        sefer_fatura_toplamlari = {}
        
        for fatura in nakliye_faturalari:
            sefer_id = fatura.Sefer_id
            if sefer_id not in sefer_fatura_toplamlari:
                sefer_fatura_toplamlari[sefer_id] = Decimal('0')
            
            sefer_fatura_toplamlari[sefer_id] += fatura.ToplamTutar
        
        # Güncelleme sayacı
        guncellenen = 0
        
        # Seferleri güncelle
        for sefer_id, toplam_tutar in sefer_fatura_toplamlari.items():
            try:
                sefer = Seferler.objects.get(id=sefer_id)
                if sefer.ucret != toplam_tutar:
                    eski_ucret = sefer.ucret
                    sefer.ucret = toplam_tutar
                    sefer.save()
                    self.stdout.write(f"Sefer #{sefer_id} (Kod: {sefer.sefer_kodu}) ücreti güncellendi: {eski_ucret} -> {toplam_tutar} EUR")
                    guncellenen += 1
                else:
                    self.stdout.write(f"Sefer #{sefer_id} (Kod: {sefer.sefer_kodu}) ücreti zaten güncel: {toplam_tutar} EUR")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Sefer #{sefer_id} güncellenirken hata: {str(e)}"))
        
        # Alternatif SQL yöntemi (eğer ORM çalışmazsa)
        if guncellenen == 0:
            self.stdout.write("ORM ile güncelleme yapılamadı, SQL sorgusu deneniyor...")
            try:
                with connection.cursor() as cursor:
                    # Her nakliye faturasının seferini güncelle
                    cursor.execute("""
                        UPDATE sefer_app_seferler s
                        SET ucret = (
                            SELECT SUM(f.ToplamTutar)
                            FROM sefer_app_faturalar f
                            WHERE f.Sefer_id = s.id AND f.FaturaTipi = 'Nakliye'
                            GROUP BY f.Sefer_id
                        )
                        WHERE id IN (
                            SELECT DISTINCT Sefer_id 
                            FROM sefer_app_faturalar 
                            WHERE FaturaTipi = 'Nakliye' AND Sefer_id IS NOT NULL
                        )
                    """)
                    guncellenen = cursor.rowcount
                    self.stdout.write(f"SQL ile toplam {guncellenen} sefer güncellendi")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"SQL ile güncelleme yapılırken hata: {str(e)}"))
        
        # Sonuç
        if guncellenen > 0:
            self.stdout.write(self.style.SUCCESS(f'Toplam {guncellenen} sefer ücreti güncellendi'))
        else:
            self.stdout.write(self.style.WARNING('Hiçbir sefer ücreti güncellenmedi')) 