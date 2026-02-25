from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from . import models


class DonorUserForm(forms.ModelForm):
    class Meta:
        model=User
        fields=['first_name','last_name','username','password']
        widgets = {
        'password': forms.PasswordInput()
        }

class DonorForm(forms.ModelForm):
    class Meta:
        model=models.Donor
        fields=['bloodgroup','address','mobile','profile_pic']

class DonationForm(forms.ModelForm):
    disease = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('Nothing')})
    )

    class Meta:
        model = models.BloodDonate
        fields = ['age', 'bloodgroup', 'disease', 'unit']
