def odeme_ekle(request, fatura_id):
    """Add a payment to an invoice."""
    fatura = get_object_or_404(Faturalar, pk=fatura_id)
    kasalar = Kasalar.objects.all().order_by('kasa_adi')
    
    if request.method == 'POST':
        odeme_tarihi = request.POST.get('odeme_tarihi')
        odeme_tutar = Decimal(request.POST.get('odeme_tutar', '0'))
        odeme_tipi = request.POST.get('odeme_tipi')
        odeme_aciklama = request.POST.get('odeme_aciklama', '')
        kasa_id = request.POST.get('kasa')
        
        # Kasa kontrolü
        if not kasa_id:
            messages.error(request, 'Ödeme için kasa seçimi zorunludur.')
            return redirect('fatura_detail', pk=fatura_id)
        
        # Create the payment
        try:
            kasa = Kasalar.objects.get(pk=kasa_id)
            
            FaturaOdeme.objects.create(
                Fatura=fatura,
                OdemeTarihi=odeme_tarihi,
                Tutar=odeme_tutar,
                OdemeTipi=odeme_tipi,
                Kasa=kasa,
                Aciklama=odeme_aciklama
            )
            
            # Update the invoice payment status
            yeni_odenen_tutar = fatura.OdenenTutar + odeme_tutar
            
            # Update payment status
            if yeni_odenen_tutar >= fatura.ToplamTutar:
                fatura.OdemeDurumu = 'Ödendi'
                fatura.OdenenTutar = fatura.ToplamTutar  # Ensure not to exceed total
            elif yeni_odenen_tutar > 0:
                fatura.OdemeDurumu = 'Kısmi Ödeme'
                fatura.OdenenTutar = yeni_odenen_tutar
            
            fatura.save()
            
            messages.success(request, f'Ödeme başarıyla eklendi. {odeme_tutar} {fatura.ParaBirimi}, {kasa.kasa_adi} kasasından.')
        except Exception as e:
            messages.error(request, f'Ödeme eklenirken hata oluştu: {str(e)}')
    
    return redirect('fatura_detail', pk=fatura_id) 