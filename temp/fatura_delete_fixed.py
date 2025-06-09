def fatura_delete(request, pk):
    """Delete an invoice."""
    try:
        # Önce faturayı kontrol edelim
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, FaturaNo, FaturaTipi, Sefer_id FROM sefer_app_faturalar WHERE id = %s", [pk])
            fatura_data = cursor.fetchone()
            
            if not fatura_data:
                messages.error(request, f"Silinecek fatura bulunamadı (ID: {pk})")
                return redirect('fatura_list')
                
            fatura_id, fatura_no, fatura_tipi, sefer_id = fatura_data
    except Exception as e:
        messages.error(request, f"Fatura kontrol edilirken hata oluştu: {str(e)}")
        return redirect('fatura_list')
    
    if request.method == 'POST':
        try:
            # Eğer nakliye faturasıysa ve bir sefere bağlıysa, seferin ücretini güncelle
            if fatura_tipi == 'Nakliye' and sefer_id:
                try:
                    # Diğer nakliye faturalarının toplamını hesapla
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT SUM(ToplamTutar) 
                            FROM sefer_app_faturalar 
                            WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye' AND id != %s
                        """, [sefer_id, pk])
                        diger_toplam = cursor.fetchone()[0] or 0
                    
                    # Sefer ücretini güncelle
                    sefer = Seferler.objects.get(id=sefer_id)
                    sefer.ucret = diger_toplam
                    sefer.save()
                    print(f"Sefer {sefer_id} ücreti {diger_toplam} EUR olarak güncellendi çünkü nakliye faturası silindi")
                except Exception as e:
                    print(f"Sefer güncelleme hatası: {str(e)}")
            
            # Önce ilişkili ürünleri silelim
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sefer_app_urunler WHERE Fatura_id = %s", [pk])
                print(f"Fatura {pk} için ürünler silindi")
            
            # Sonra ilişkili ödemeleri silelim (tablo varsa)
            with connection.cursor() as cursor:
                # Tablonun var olup olmadığını kontrol et
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sefer_app_faturaodeme'")
                table_exists = cursor.fetchone() is not None
                
                if table_exists:
                    cursor.execute("DELETE FROM sefer_app_faturaodeme WHERE Fatura_id = %s", [pk])
                    print(f"Fatura {pk} için ödemeler silindi")
            
            # Son olarak faturayı silelim
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sefer_app_faturalar WHERE id = %s", [pk])
                print(f"Fatura {pk} silindi")
            
            messages.success(request, f'"{fatura_no}" numaralı fatura başarıyla silindi.')
            return redirect('fatura_list')
        except Exception as e:
            error_message = f"Fatura silinemedi: {str(e)}"
            print(error_message)
            messages.error(request, error_message)
            # GET isteği gibi onay sayfasını tekrar göster
            return render(request, 'sefer_app/fatura_delete.html', {
                'fatura': {
                    'id': fatura_id,
                    'FaturaNo': fatura_no
                }
            })
    
    # Fatura detaylarını alalım
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT f.*, fr.FirmaAdi 
                FROM sefer_app_faturalar f 
                LEFT JOIN sefer_app_firmalar fr ON f.Firma_id = fr.id 
                WHERE f.id = %s
            """, [pk])
            
            columns = [col[0] for col in cursor.description]
            fatura_data = cursor.fetchone()
            
            if not fatura_data:
                messages.error(request, f"Silinecek fatura bulunamadı (ID: {pk})")
                return redirect('fatura_list')
                
            fatura = dict(zip(columns, fatura_data))
            fatura['Firma'] = {'FirmaAdi': fatura.get('FirmaAdi')}
            
            # Tarihleri datetime formatına çevirelim
            from datetime import datetime
            if fatura.get('FaturaTarihi'):
                try:
                    fatura['FaturaTarihi'] = datetime.strptime(fatura['FaturaTarihi'], '%Y-%m-%d')
                except:
                    pass
    except Exception as e:
        messages.error(request, f"Fatura bilgileri alınırken hata oluştu: {str(e)}")
        return redirect('fatura_list')
    
    # GET isteği için onay sayfası göster
    return render(request, 'sefer_app/fatura_delete.html', {'fatura': fatura}) 