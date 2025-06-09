def fatura_create(request):
    """Create a new invoice."""
    # Get all companies and trips for select options
    firmalar = Firmalar.objects.all().order_by('FirmaAdi')
    seferler = Seferler.objects.all().order_by('-cikis_tarihi')
    
    # Generate default fatura number in FYYYYAAGGX format
    today = datetime.now()
    date_part = f"F{today.year}{today.month:02d}{today.day:02d}"
    
    # Get the last invoice number with today's date pattern to determine sequential number
    last_fatura = Faturalar.objects.filter(FaturaNo__startswith=date_part).order_by('-FaturaNo').first()
    
    if last_fatura:
        # Extract the last sequence number and increment
        try:
            # Daha güvenli bir yöntem - tarih kısmını çıkarıp kalan kısmı sayıya dönüştür
            seq_part = last_fatura.FaturaNo[len(date_part):]
            if seq_part.isdigit():
                last_seq = int(seq_part)
                default_fatura_no = f"{date_part}{last_seq + 1}"
            else:
                default_fatura_no = f"{date_part}1"
        except (ValueError, IndexError):
            default_fatura_no = f"{date_part}1"
    else:
        # First invoice of the day
        default_fatura_no = f"{date_part}1"
    
    if request.method == 'POST':
        # Get form data
        fatura_tipi = request.POST.get('fatura_tipi')
        firma_id = request.POST.get('firma')
        fatura_no = request.POST.get('fatura_no')
        
        # Kontrol et - aynı fatura numarası var mı?
        if Faturalar.objects.filter(FaturaNo=fatura_no).exists():
            messages.error(request, f"'{fatura_no}' numaralı fatura zaten var. Lütfen farklı bir numara girin.")
            context = {
                'firmalar': firmalar,
                'seferler': seferler,
                'default_fatura_no': default_fatura_no,
            }
            return render(request, 'sefer_app/fatura_form.html', context)
        
        fatura_tarihi = request.POST.get('fatura_tarihi')
        vade_tarihi = request.POST.get('vade_tarihi', None)
        ilgili_sefer_id = request.POST.get('ilgili_sefer')
        aciklama = request.POST.get('aciklama', '')
        notlar = request.POST.get('notlar', '')
        
        try:
            # Decimal değerleri güvenli şekilde dönüştür
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

            ara_toplam_str = request.POST.get('ara_toplam', '0')
            kdv_orani_str = request.POST.get('kdv_orani', '0')
            genel_toplam_str = request.POST.get('genel_toplam', '0')
            odenen_tutar_str = request.POST.get('odenen_tutar', '0')

            ara_toplam = safe_decimal(ara_toplam_str)
            kdv_orani = safe_decimal(kdv_orani_str)
            genel_toplam = safe_decimal(genel_toplam_str)
            odenen_tutar = safe_decimal(odenen_tutar_str)

            print(f"Fiyat bilgileri: AraToplam={ara_toplam}, KDV={kdv_orani}, GenelToplam={genel_toplam}")
        except Exception as e:
            messages.error(request, f"Fiyat bilgilerinde dönüşüm hatası: {str(e)}")
            context = {
                'firmalar': firmalar,
                'seferler': seferler,
                'default_fatura_no': default_fatura_no,
            }
            return render(request, 'sefer_app/fatura_form.html', context)
        
        odeme_durumu = request.POST.get('odeme_durumu', 'Ödenmedi')
        
        # Doğrudan SQL ile fatura oluştur - model ve veritabanı uyumsuzluğunu aşmak için
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sefer_app_faturalar (
                        FaturaTipi, Firma_id, FaturaNo, FaturaTarihi, VadeTarihi,
                        ParaBirimi, AraToplam, KDVOrani, ToplamTutar, OdenenTutar,
                        OdemeDurumu, Aciklama, Notlar, Sefer_id, KurEUR, ToplamEUR
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    fatura_tipi, firma_id, fatura_no, fatura_tarihi, vade_tarihi,
                    'EUR', ara_toplam, kdv_orani, genel_toplam, odenen_tutar,
                    odeme_durumu, aciklama, notlar, ilgili_sefer_id if ilgili_sefer_id else None, 
                    1.0, genel_toplam  # KurEUR değeri 1.0, ToplamEUR değeri genel_toplam ile aynı
                ])
                
                # SQLite'da son eklenen kaydın ID'sini al
                fatura_id = cursor.lastrowid
        except Exception as e:
            error_message = f"Fatura oluşturulurken hata oluştu: {str(e)}"
            print(error_message)
            messages.error(request, error_message)
            context = {
                'firmalar': firmalar,
                'seferler': seferler,
                'default_fatura_no': default_fatura_no,
            }
            return render(request, 'sefer_app/fatura_form.html', context)
        
        # Get product data from form (arrays)
        urunler = request.POST.getlist('urun[]')
        aciklamalar = request.POST.getlist('aciklama[]')
        miktarlar = request.POST.getlist('miktar[]')
        birimler = request.POST.getlist('birim[]')
        birim_fiyatlar = request.POST.getlist('birim_fiyat[]')
        kdv_oranlari = request.POST.getlist('kdv[]')
        toplamlar = request.POST.getlist('toplam[]')
        
        # Create invoice items - raw SQL kullanarak urunler ekleme
        for i in range(len(urunler)):
            if urunler[i]:  # Skip empty items
                try:
                    print(f"Ürün ekleniyor: {urunler[i]}, Açıklama: {aciklamalar[i] if i < len(aciklamalar) else ''}")

                    # Güvenli decimal dönüşümleri
                    miktar_str = miktarlar[i] if i < len(miktarlar) else '0'
                    birim_fiyat_str = birim_fiyatlar[i] if i < len(birim_fiyatlar) else '0'
                    kdv_oran_str = kdv_oranlari[i] if i < len(kdv_oranlari) else '0'
                    toplam_str = toplamlar[i] if i < len(toplamlar) else '0'

                    print(f"Ürün #{i + 1} değerleri: Miktar={miktar_str}, BirimFiyat={birim_fiyat_str}, KDV={kdv_oran_str}, Toplam={toplam_str}")

                    miktar = safe_decimal(miktar_str)
                    birim_fiyat = safe_decimal(birim_fiyat_str)
                    kdv_oran = safe_decimal(kdv_oran_str)
                    toplam = safe_decimal(toplam_str)

                    # Veritabanındaki alan isimleri farklı olabilir, bu yüzden raw SQL kullanıyoruz
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO sefer_app_urunler (
                                Fatura_id, UrunHizmetAdi, Miktar, 
                                Birim, BirimFiyat, KDVOrani, Toplam
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, [
                            fatura_id,
                            urunler[i],
                            miktar,
                            birimler[i] if i < len(birimler) else 'Adet',
                            birim_fiyat,
                            kdv_oran,
                            toplam
                        ])

                        urun_id = cursor.lastrowid
                        print(f"Ürün başarıyla eklendi. ID: {urun_id}")
                except Exception as e:
                    print(f"Ürün eklenirken hata oluştu: {str(e)}")
                    # Hatayı log et ama devam et
                    continue
        
        # Create payment record if paid
        if odeme_durumu != 'Ödenmedi' and odenen_tutar > 0:
            try:
                # Ödeme için kasa seçimi
                odeme_kasa_id = request.POST.get('odeme_kasa')

                if odeme_kasa_id:
                    odeme_kasa = Kasalar.objects.get(pk=odeme_kasa_id)

                    FaturaOdeme.objects.create(
                        Fatura_id=fatura_id,
                        OdemeTarihi=fatura_tarihi,
                        Tutar=odenen_tutar,
                        OdemeTipi='Nakit',
                        Kasa=odeme_kasa,
                        Aciklama='İlk ödeme'
                    )
                else:
                    messages.warning(request, 'Ödeme tutarı girildi ancak kasa seçilmediği için ödeme kaydedilmedi.')
            except Exception as e:
                print(f"Ödeme kaydı oluşturma hatası: {str(e)}")
                messages.error(request, f"Ödeme kaydı oluşturulurken hata: {str(e)}")

        # Eğer nakliye faturasıysa ve bir sefere bağlıysa, seferin ücretini güncelle
        if fatura_tipi == 'Nakliye' and ilgili_sefer_id:
            try:
                # TÜM ilgili nakliye faturalarının toplamını al
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT SUM(ToplamTutar) 
                        FROM sefer_app_faturalar 
                        WHERE Sefer_id = %s AND FaturaTipi = 'Nakliye'
                    """, [ilgili_sefer_id])
                    toplam_nakliye = cursor.fetchone()[0]
                    
                if toplam_nakliye:
                    sefer = Seferler.objects.get(id=ilgili_sefer_id)
                    sefer.ucret = toplam_nakliye
                    sefer.save()
                    print(f"Sefer {ilgili_sefer_id} ücreti {toplam_nakliye} EUR olarak güncellendi")
            except Exception as e:
                print(f"Sefer güncelleme hatası: {str(e)}")
        
        messages.success(request, 'Fatura başarıyla oluşturuldu.')
        return redirect('fatura_detail', pk=fatura_id)
    
    context = {
        'firmalar': firmalar,
        'seferler': seferler,
        'default_fatura_no': default_fatura_no,
    }
    return render(request, 'sefer_app/fatura_form.html', context) 