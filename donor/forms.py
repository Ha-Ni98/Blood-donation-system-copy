from django import forms
from django.utils.translation import gettext_lazy as _
from . import models

# Donor user/profile forms have been removed. 
# Registration is now handled by unified forms in blood/forms.py using AppUser and DonorProfile.

class DonationForm(forms.ModelForm):
    disease = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('Nothing')})
    )

    class Meta:
        model = models.BloodDonate
        fields = ['age', 'bloodgroup', 'disease', 'unit']
