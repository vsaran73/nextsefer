from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from ..models import UserProfile
from django import forms
import logging
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

# Django logger
logger = logging.getLogger('sefer_app')

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, label="Ad")
    last_name = forms.CharField(max_length=30, required=False, label="Soyad")
    email = forms.EmailField(required=False, label="E-posta")

    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'position', 'phone_number', 'address', 'date_of_birth']
        labels = {
            'profile_picture': 'Profil Resmi',
            'position': 'Pozisyon',
            'phone_number': 'Telefon Numarası',
            'address': 'Adres',
            'date_of_birth': 'Doğum Tarihi',
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        labels = {'username': 'Kullanıcı Adı'}

@login_required
def profile_view(request):
    """View and edit user profile"""
    logger.debug("profile_view çağrıldı - Kullanıcı: %s", request.user.username)
    user = request.user
    
    try:
        profile = get_object_or_404(UserProfile, user=user)
        logger.debug("Profil bulundu - Kullanıcı: %s", user.username)
    except Exception as e:
        logger.error("Profil bulunamadı veya hata oluştu: %s", str(e))
        # Eğer profil yoksa otomatik oluşturalım
        profile = UserProfile.objects.create(user=user)
        logger.info("Yeni profil oluşturuldu - Kullanıcı: %s", user.username)
    
    password_form = PasswordChangeForm(user)
    username_form = UsernameChangeForm(instance=user)

    if request.method == 'POST':
        form = UserProfileForm(instance=profile, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
        if 'update_profile' in request.POST:
            form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()
                form.save()
                messages.success(request, "Profil bilgileriniz başarıyla güncellendi.")
                return redirect('profile')
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Şifreniz başarıyla değiştirildi.')
                return redirect('profile')
            else:
                messages.error(request, 'Şifre değiştirilirken hata oluştu. Lütfen kontrol edin.')
        elif 'change_username' in request.POST:
            username_form = UsernameChangeForm(request.POST, instance=user)
            if username_form.is_valid():
                username_form.save()
                messages.success(request, 'Kullanıcı adınız başarıyla değiştirildi.')
                return redirect('profile')
            else:
                messages.error(request, 'Kullanıcı adı değiştirilirken hata oluştu. Lütfen kontrol edin.')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
        password_form = PasswordChangeForm(user)
        username_form = UsernameChangeForm(instance=user)

    context = {
        'form': form,
        'profile': profile,
        'password_form': password_form,
        'username_form': username_form,
    }
    return render(request, 'sefer_app/profile.html', context)

@login_required
def admin_to_profile_redirect(request):
    """Redirect from admin to custom profile page"""
    logger.debug("admin_to_profile_redirect çağrıldı - Kullanıcı: %s", request.user.username)
    # Redirect to absolute URL path instead of using reverse URL name
    return HttpResponseRedirect('/profile/') 