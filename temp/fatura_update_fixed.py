def fatura_update(request, pk):
    """Update an existing invoice."""
    fatura = get_object_or_404(Faturalar, pk=pk)
    firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    seferler = Seferler.objects.all().order_by('-cikis_tarihi')
    
    # Faturaya ait ürünleri al
    try:
        urunler = list(Urunler.objects.filter(Fatura_id=pk))
        print(f"ORM ile {len(urunler)} ürün bulundu")
    except Exception as e:
        print(f"Ürünleri alma hatası: {str(e)}")
        urunler = []
        
        # ORM başarısız olduysa SQL ile dene
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM sefer_app_urunler WHERE Fatura_id = %s", [pk])
                columns = [col[0] for col in cursor.description]
                urunler = []
                for row in cursor.fetchall():
                    urun_dict = dict(zip(columns, row))
                    urunler.append(urun_dict)
                print(f"SQL ile {len(urunler)} ürün bulundu")
        except Exception as e:
            print(f"SQL ile ürün alma hatası: {str(e)}")
    
    if request.method == 'POST':
        print("Fatura güncelleme POST isteği alındı")
        
        # Formdan gelen verileri al
        try:
            firma_id = request.POST.get('firma')
            fatura_no = request.POST.get('fatura_no')
            fatura_tipi = request.POST.get('fatura_tipi', fatura.FaturaTipi)
            fatura_tarihi = request.POST.get('fatura_tarihi')
            vade_tarihi = request.POST.get('vade_tarihi')
            ilgili_sefer_id = request.POST.get('ilgili_sefer')
            aciklama = request.POST.get('aciklama', '')
            notlar = request.POST.get('notlar', '')
        
            # Sayısal değerleri dönüştür - daha güvenli yöntemle
            def safe_decimal(value, default=0):
                if not value:
                    return Decimal(default)
                # Değeri temizle ve düzgün işle
                try:
                    # Önce sayısal değeri temizle
                    clean_value = value.strip()
                    
                    # Türkçe format kontrolü (1.234,56 formatı)
                    if ',' in clean_value and '.' in clean_value and clean_value.rindex('.') < clean_value.rindex(','):
                        # Türkçe format - önce binlik ayırıcıları kaldır, sonra virgülü noktaya çevir
                        clean_value = clean_value.replace('.', '').replace(',', '.')
                    elif ',' in clean_value and '.' not in clean_value:
                        # Sadece virgül var - virgülü noktaya çevir
                        clean_value = clean_value.replace(',', '.')
                    # Diğer durumlarda (1,234.56 veya 1234.56) herhangi bir değişiklik yapma
                    
                    print(f"Decimal dönüşümü: {value} -> {clean_value}")
                    return Decimal(clean_value)
                except Exception as e:
                    print(f"Decimal dönüşüm hatası: {value} - {str(e)}")
                    return Decimal(default)
            
            ara_toplam = safe_decimal(request.POST.get('ara_toplam', '0'))
            kdv_orani = safe_decimal(request.POST.get('kdv_orani', '0'))
            genel_toplam = safe_decimal(request.POST.get('genel_toplam', '0'))
            odenen_tutar = safe_decimal(request.POST.get('odenen_tutar', '0'))
            odeme_durumu = request.POST.get('odeme_durumu', 'Ödenmedi')
            
            # Eski değerleri sakla
            eski_fatura_tipi = fatura.FaturaTipi
            eski_sefer_id = fatura.Sefer_id if hasattr(fatura, 'Sefer_id') else None
            
            print(f"Fatura başlık bilgileri işleniyor: {fatura_no}, {fatura_tipi}, {firma_id}, {ilgili_sefer_id}")
            print(f"Sayısal değerler: AraToplam={ara_toplam}, KDV={kdv_orani}, Toplam={genel_toplam}")
            
            # 1. Adım: Faturayı güncelle
            try:
                # Django ORM ile güncelleme yap
                fatura.Firma_id = firma_id
                fatura.FaturaNo = fatura_no
                fatura.FaturaTipi = fatura_tipi
                fatura.FaturaTarihi = fatura_tarihi
                fatura.VadeTarihi = vade_tarihi if vade_tarihi else None
                fatura.AraToplam = ara_toplam
                fatura.KDVOrani = kdv_orani
                fatura.ToplamTutar = genel_toplam
                fatura.OdenenTutar = odenen_tutar
                fatura.OdemeDurumu = odeme_durumu
                fatura.Aciklama = aciklama
                fatura.Notlar = notlar
                fatura.Sefer_id = ilgili_sefer_id if ilgili_sefer_id else None
                fatura.KurEUR = Decimal('1.0')
                fatura.ToplamEUR = genel_toplam
                
                fatura.save()
                print(f"Fatura #{pk} başarıyla güncellendi")
            except Exception as e:
                print(f"Fatura güncelleme hatası (ORM): {str(e)}")
                # ORM başarısız olursa SQL dene
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE sefer_app_faturalar SET
                                Firma_id = %s, FaturaNo = %s, FaturaTipi = %s, 
                                FaturaTarihi = %s, VadeTarihi = %s, AraToplam = %s,
                                KDVOrani = %s, ToplamTutar = %s, OdenenTutar = %s,
                                OdemeDurumu = %s, Aciklama = %s, Notlar = %s,
                                Sefer_id = %s, KurEUR = %s, ToplamEUR = %s
                            WHERE id = %s
                        """, [
                            firma_id, fatura_no, fatura_tipi,
                            fatura_tarihi, vade_tarihi, ara_toplam,
                            kdv_orani, genel_toplam, odenen_tutar,
                            odeme_durumu, aciklama, notlar, 
                            ilgili_sefer_id if ilgili_sefer_id else None, 1.0, genel_toplam,
                            pk
                        ])
                        print(f"Fatura #{pk} SQL ile güncellendi")
                except Exception as e:
                    print(f"Fatura güncelleme hatası (SQL): {str(e)}")
                    messages.error(request, f"Fatura güncellenirken hata oluştu: {str(e)}")
                    context = {
                        'fatura': fatura,
                        'firmalar': firmalar,
                        'seferler': seferler,
                        'urunler': urunler,
                    }
                    return render(request, 'sefer_app/fatura_form.html', context)
            
            # 2. Adım: Sefer ücretlerini güncelle (nakliye faturası ise)
            # Eski sefer ve yeni sefer farklıysa her ikisinin de ücretlerini güncelle
            if eski_fatura_tipi == 'Nakliye' and eski_sefer_id and eski_sefer_id != ilgili_sefer_id:
                try:
                    # Eski sefere ait nakliye faturalarının toplamını hesapla
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT SUM(ToplamTutar) 
                            FROM sefer_app_faturalar 
                            WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye' AND id != %s
                        """, [eski_sefer_id, pk])
                        kalan_toplam = cursor.fetchone()[0] or 0
                        
                    # Eski seferin ücretini güncelle
                    eski_sefer = Seferler.objects.get(id=eski_sefer_id)
                    eski_sefer.ucret = kalan_toplam
                    eski_sefer.save()
                    print(f"Eski sefer {eski_sefer_id} ücreti {kalan_toplam} EUR olarak güncellendi")
                except Exception as e:
                    print(f"Eski sefer ücret güncelleme hatası: {str(e)}")
            
            # Yeni sefer varsa ve fatura tipi nakliye ise, yeni seferin ücretini güncelle
            if fatura_tipi == 'Nakliye' and ilgili_sefer_id:
                try:
                    # Sefer için toplam nakliye tutarını hesapla
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT SUM(ToplamTutar) 
                            FROM sefer_app_faturalar 
                            WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye'
                        """, [ilgili_sefer_id])
                        toplam_nakliye = cursor.fetchone()[0] or 0
                    
                    # Seferin ücretini güncelle
                    sefer = Seferler.objects.get(id=ilgili_sefer_id)
                    sefer.ucret = toplam_nakliye
                    sefer.save()
                    print(f"Sefer {ilgili_sefer_id} ücreti {toplam_nakliye} EUR olarak güncellendi")
                except Exception as e:
                    print(f"Yeni sefer ücret güncelleme hatası: {str(e)}")
            
            # 3. Adım: Ürünleri güncelle
            print("Fatura ürünleri güncelleniyor...")
            
            # Mevcut ürünleri sil
            try:
                # Önce ORM ile silmeyi dene
                Urunler.objects.filter(Fatura_id=pk).delete()
                print(f"Fatura #{pk} ürünleri silindi (ORM)")
            except Exception as e:
                print(f"Ürün silme hatası (ORM): {str(e)}")
                # ORM başarısız olursa SQL dene
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM sefer_app_urunler WHERE Fatura_id = %s", [pk])
                        print(f"Fatura #{pk} ürünleri silindi (SQL)")
                except Exception as e:
                    print(f"Ürün silme hatası (SQL): {str(e)}")
            
            # Formdan ürün verilerini al
            urunler_data = request.POST.getlist('urun[]')
            miktarlar = request.POST.getlist('miktar[]')
            birimler = request.POST.getlist('birim[]')
            birim_fiyatlar = request.POST.getlist('birim_fiyat[]')
            kdv_oranlari = request.POST.getlist('kdv[]')
            toplamlar = request.POST.getlist('toplam[]')
            
            print(f"Eklenecek ürün sayısı: {len(urunler_data)}")
            
            # Yeni ürünleri ekle
            for i in range(len(urunler_data)):
                if not urunler_data[i]:  # Boş ürünleri atla
                    continue
                
                try:
                    # Değerleri güvenli şekilde dönüştür
                    miktar_str = miktarlar[i] if i < len(miktarlar) else '0'
                    birim = birimler[i] if i < len(birimler) else 'Adet'
                    birim_fiyat_str = birim_fiyatlar[i] if i < len(birim_fiyatlar) else '0'
                    kdv_oran_str = kdv_oranlari[i] if i < len(kdv_oranlari) else '0'
                    toplam_str = toplamlar[i] if i < len(toplamlar) else '0'
                    
                    print(f"Ürün #{i+1} değerleri: Miktar={miktar_str}, BirimFiyat={birim_fiyat_str}, KDV={kdv_oran_str}, Toplam={toplam_str}")
                    
                    miktar = safe_decimal(miktar_str)
                    birim_fiyat = safe_decimal(birim_fiyat_str)
                    kdv_oran = safe_decimal(kdv_oran_str)
                    toplam = safe_decimal(toplam_str)
                    
                    print(f"Ürün ekleniyor: {urunler_data[i]}, Miktar: {miktar}, Birim: {birim}, BirimFiyat: {birim_fiyat}, Toplam: {toplam}")
                    
                    # Önce ORM ile eklemeyi dene
                    try:
                        urun = Urunler(
                            Fatura_id=pk,
                            UrunHizmetAdi=urunler_data[i],
                            Miktar=miktar,
                            Birim=birim,
                            BirimFiyat=birim_fiyat,
                            KDVOrani=kdv_oran,
                            Toplam=toplam
                        )
                        urun.save()
                        print(f"Ürün başarıyla eklendi (ORM): {urun.id}")
                    except Exception as e:
                        print(f"Ürün ekleme hatası (ORM): {str(e)}")
                        # ORM başarısız olursa SQL dene
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute("""
                                    INSERT INTO sefer_app_urunler (
                                        Fatura_id, UrunHizmetAdi, Miktar, 
                                        Birim, BirimFiyat, KDVOrani, Toplam
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    pk, urunler_data[i], miktar, 
                                    birim, birim_fiyat, kdv_oran, toplam
                                ])
                                print("Ürün başarıyla eklendi (SQL)")
                        except Exception as e:
                            print(f"Ürün ekleme hatası (SQL): {str(e)}")
                except Exception as e:
                    print(f"Ürün #{i+1} işleme hatası: {str(e)}")
            
            messages.success(request, 'Fatura başarıyla güncellendi.')
            return redirect('fatura_detail', pk=pk)
            
        except Exception as e:
            error_message = f"Fatura güncelleme işleminde hata: {str(e)}"
            print(error_message)
            messages.error(request, error_message)
            context = {
                'fatura': fatura,
                'firmalar': firmalar,
                'seferler': seferler,
                'urunler': urunler,
            }
            return render(request, 'sefer_app/fatura_form.html', context)
    
    # GET isteği için form
    context = {
        'fatura': fatura,
        'firmalar': firmalar,
        'seferler': seferler,
        'urunler': urunler,
    }
    return render(request, 'sefer_app/fatura_form.html', context) 