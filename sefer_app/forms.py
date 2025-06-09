from django import forms
from .models import FirmaBilgi
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class FirmaBilgiForm(forms.ModelForm):
    class Meta:
        model = FirmaBilgi
        fields = ['unvan', 'adres', 'telefon', 'eposta', 'vergi_no', 'vergi_dairesi', 'web']
        widgets = {
            'adres': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unvan'].required = True
        self.fields['adres'].required = True
        self.fields['telefon'].required = True

class KullaniciKurulumForm(forms.ModelForm):
    password1 = forms.CharField(label='Şifre', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Şifre (Tekrar)', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Şifreler eşleşmiyor!')
        return cleaned_data 