"""
Expense (Masraf) related views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

from ..models import SeferMasraf, Seferler, Kasalar, ParaBirimleri
from .helpers import safe_decimal
from .sefer_views import generate_masraf_belge_no

def masraf_list(request):
    """List all expenses."""
    masraflar = SeferMasraf.objects.all().order_by('-Tarih')
    
    # Filter parameters
    baslangic_tarihi = request.GET.get('baslangic_tarihi', '')
    bitis_tarihi = request.GET.get('bitis_tarihi', '')
    masraf_turu = request.GET.get('masraf_turu', '')
    arama = request.GET.get('arama', '')
    
    # Apply filters
    if baslangic_tarihi:
        masraflar = masraflar.filter(Tarih__gte=baslangic_tarihi)
        
    if bitis_tarihi:
        masraflar = masraflar.filter(Tarih__lte=bitis_tarihi)
        
    if masraf_turu:
        masraflar = masraflar.filter(MasrafTipi=masraf_turu)
        
    if arama:
        masraflar = masraflar.filter(
            Q(Aciklama__icontains=arama) | 
            Q(BelgeNo__icontains=arama) |
            Q(Sefer__rota__icontains=arama)
        )
    
    # Calculate total expense with output_field to fix mixed types issue
    toplam_masraf = masraflar.aggregate(total=Coalesce(Sum('TutarEUR'), 0, output_field=DecimalField()))['total'] or 0
    
    # Get unique expense types for dropdown
    masraf_turleri = SeferMasraf.objects.values_list('MasrafTipi', flat=True).distinct()
    
    context = {
        'masraflar': masraflar,
        'toplam_masraf': toplam_masraf,
        'masraf_turleri': masraf_turleri,
        'baslangic_tarihi_filtre': baslangic_tarihi,
        'bitis_tarihi_filtre': bitis_tarihi,
        'masraf_turu_filtre': masraf_turu,
        'arama_filtre': arama
    }
    return render(request, 'sefer_app/masraf_list.html', context)


def masraf_create(request):
    """Create a new expense."""
    seferler = Seferler.objects.order_by('-cikis_tarihi')
    kasalar = Kasalar.objects.order_by('kasa_adi')
    para_birimleri = ParaBirimleri.objects.all().order_by('kod')
    
    if request.method == 'POST':
        try:
            masraf_tipi = request.POST.get('MasrafTipi')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            para_birimi = request.POST.get('para_birimi', 'EUR')
            kur = safe_decimal(request.POST.get('kur', '1.0'))
            tutar_eur = tutar / kur if kur > 0 else tutar  # Convert to EUR
            tarih = request.POST.get('tarih')
            sefer_id = request.POST.get('sefer')
            kasa_id = request.POST.get('kasa')
            belge_no = request.POST.get('belge_no', '')
            
            # Auto-generate document number if none provided
            if not belge_no:
                belge_no = generate_masraf_belge_no()
                print(f"Generated expense document number: {belge_no}")
            
            # Get related objects
            sefer = None
            if sefer_id:
                try:
                    sefer = Seferler.objects.get(id=sefer_id)
                except:
                    sefer = None
            
            kasa = None
            if kasa_id:
                try:
                    kasa = Kasalar.objects.get(id=kasa_id)
                except:
                    kasa = None
            
            if tarih and masraf_tipi and kasa:
                # Create expense record
                masraf = SeferMasraf(
                    MasrafTipi=masraf_tipi,
                    Tutar=tutar,
                    ParaBirimi=para_birimi,
                    KurEUR=kur,
                    TutarEUR=tutar_eur,
                    Tarih=tarih,
                    BelgeNo=belge_no,
                    Aciklama=request.POST.get('aciklama', ''),
                    OdemeYontemi=request.POST.get('odeme_yontemi', 'Nakit'),
                    Sefer=sefer,
                    Kasa=kasa
                )
                
                masraf.save()
                
                messages.success(request, f"{masraf_tipi} masrafı başarıyla kaydedildi.")
                
                # Redirect based on whether this was created from a trip detail page
                if 'sefer' in request.GET:
                    return redirect('sefer_detail', pk=request.GET.get('sefer'))
                return redirect('masraf_list')
            else:
                messages.error(request, "Masraf türü, tarih ve kasa seçimi zorunludur.")
        except Exception as e:
            messages.error(request, f"Masraf kaydedilirken bir hata oluştu: {str(e)}")
    
    context = {
        'seferler': seferler, 
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/masraf_form.html', context)


def masraf_update(request, pk):
    """Update an expense."""
    masraf = get_object_or_404(SeferMasraf, pk=pk)
    seferler = Seferler.objects.order_by('-cikis_tarihi')
    kasalar = Kasalar.objects.order_by('kasa_adi')
    para_birimleri = ParaBirimleri.objects.all().order_by('kod')
    
    if request.method == 'POST':
        try:
            masraf_tipi = request.POST.get('MasrafTipi')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            para_birimi = request.POST.get('para_birimi', 'EUR')
            kur = safe_decimal(request.POST.get('kur', '1.0'))
            tutar_eur = tutar / kur if kur > 0 else tutar  # Convert to EUR
            tarih = request.POST.get('tarih')
            sefer_id = request.POST.get('sefer')
            kasa_id = request.POST.get('kasa')
            
            if not masraf_tipi or not tarih:
                messages.error(request, 'Masraf türü ve tarih zorunludur.')
                context = {
                    'masraf': masraf, 
                    'seferler': seferler,
                    'kasalar': kasalar,
                    'para_birimleri': para_birimleri,
                    'today': timezone.now().date()
                }
                return render(request, 'sefer_app/masraf_form.html', context)
            
            # Update expense record
            masraf.MasrafTipi = masraf_tipi
            masraf.Tarih = tarih
            masraf.BelgeNo = request.POST.get('belge_no', '')
            masraf.Aciklama = request.POST.get('aciklama', '')
            masraf.Tutar = tutar
            masraf.ParaBirimi = para_birimi
            masraf.KurEUR = kur
            masraf.TutarEUR = tutar_eur
            masraf.OdemeYontemi = request.POST.get('odeme_yontemi', 'Nakit')
            
            # Update related objects
            if sefer_id:
                try:
                    masraf.Sefer = Seferler.objects.get(id=sefer_id)
                except:
                    masraf.Sefer = None
            else:
                masraf.Sefer = None
            
            if kasa_id:
                try:
                    masraf.Kasa = Kasalar.objects.get(id=kasa_id)
                except:
                    messages.error(request, 'Seçilen kasa bulunamadı.')
                    return render(request, 'sefer_app/masraf_form.html', {
                        'masraf': masraf, 
                        'seferler': seferler,
                        'kasalar': kasalar,
                        'para_birimleri': para_birimleri,
                        'today': timezone.now().date()
                    })
            
            masraf.save()
            
            messages.success(request, "Masraf kaydı başarıyla güncellendi.")
            
            # Redirect based on whether this was updated from a trip detail page
            if masraf.Sefer:
                return redirect('sefer_detail', pk=masraf.Sefer.id)
            return redirect('masraf_list')
            
        except Exception as e:
            messages.error(request, f'Masraf güncelleme hatası: {str(e)}')
    
    context = {
        'masraf': masraf, 
        'seferler': seferler,
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/masraf_form.html', context)


def masraf_sil(request, pk):
    """Delete an expense."""
    masraf = get_object_or_404(SeferMasraf, pk=pk)
    
    if request.method == 'POST':
        try:
            # Remember related trip for redirect
            sefer = masraf.Sefer
            
            masraf.delete()
            messages.success(request, "Masraf kaydı başarıyla silindi.")
            
            # Redirect based on whether this was deleted from a trip detail page
            if sefer:
                return redirect('sefer_detail', pk=sefer.id)
            else:
                return redirect('masraf_list')
            
        except Exception as e:
            messages.error(request, f'Masraf silme hatası: {str(e)}')
            
            # Redirect based on source
            if masraf.Sefer:
                return redirect('sefer_detail', pk=masraf.Sefer.id)
            else:
                return redirect('masraf_list')
    
    context = {'masraf': masraf}
    return render(request, 'sefer_app/masraf_confirm_delete.html', context)


# Add alias for masraf_delete
masraf_delete = masraf_sil


def masraf_ekle(request, sefer_id):
    """Add an expense to a specific trip."""
    sefer = get_object_or_404(Seferler, pk=sefer_id)
    kasalar = Kasalar.objects.order_by('kasa_adi')
    para_birimleri = ParaBirimleri.objects.all().order_by('kod')
    
    if request.method == 'POST':
        try:
            masraf_tipi = request.POST.get('MasrafTipi')
            tutar = safe_decimal(request.POST.get('tutar', '0'))
            para_birimi = request.POST.get('para_birimi', 'EUR')
            kur = safe_decimal(request.POST.get('kur', '1.0'))
            tutar_eur = tutar / kur if kur > 0 else tutar  # Convert to EUR
            tarih = request.POST.get('tarih')
            kasa_id = request.POST.get('kasa')
            belge_no = request.POST.get('belge_no', '')
            
            # Auto-generate document number if none provided
            if not belge_no:
                belge_no = generate_masraf_belge_no()
                print(f"Generated expense document number: {belge_no}")
            
            if not masraf_tipi or not tarih or not kasa_id:
                messages.error(request, 'Masraf türü, tarih ve kasa seçimi zorunludur.')
                context = {
                    'sefer': sefer, 
                    'kasalar': kasalar,
                    'para_birimleri': para_birimleri,
                    'today': timezone.now().date()
                }
                return render(request, 'sefer_app/masraf_sefer_form.html', context)
            
            # Get cash register
            try:
                kasa = Kasalar.objects.get(id=kasa_id)
            except Kasalar.DoesNotExist:
                messages.error(request, 'Seçilen kasa bulunamadı.')
                context = {
                    'sefer': sefer, 
                    'kasalar': kasalar,
                    'para_birimleri': para_birimleri,
                    'today': timezone.now().date()
                }
                return render(request, 'sefer_app/masraf_sefer_form.html', context)
            
            # Create expense record
            masraf = SeferMasraf(
                MasrafTipi=masraf_tipi,
                Tutar=tutar,
                ParaBirimi=para_birimi,
                KurEUR=kur,
                TutarEUR=tutar_eur,
                Tarih=tarih,
                BelgeNo=belge_no,
                Aciklama=request.POST.get('aciklama', ''),
                OdemeYontemi=request.POST.get('odeme_yontemi', 'Nakit'),
                Sefer=sefer,
                Kasa=kasa
            )
            masraf.save()
            
            messages.success(request, f"{masraf_tipi} masrafı başarıyla kaydedildi.")
            return redirect('sefer_detail', pk=sefer_id)
            
        except Exception as e:
            messages.error(request, f'Masraf oluşturma hatası: {str(e)}')
    
    context = {
        'sefer': sefer, 
        'kasalar': kasalar,
        'para_birimleri': para_birimleri,
        'today': timezone.now().date()
    }
    return render(request, 'sefer_app/masraf_sefer_form.html', context) 