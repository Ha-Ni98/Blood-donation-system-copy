from django import forms
from . import models
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User


class BloodForm(forms.ModelForm):
    class Meta:
        model=models.Stock
        fields=['bloodgroup','unit']

# RequestForm removed — legacy BloodRequest fields no longer exist.
# BloodRequestForm will be created in Sprint 3.


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'

class SignupUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['username', 'password']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError(
                "Password and Confirm Password does not match"
            )

class SignupAppUserForm(forms.ModelForm):
    terms = forms.BooleanField(required=True, label="I agree to the terms and conditions")

    class Meta:
        model = models.AppUser
        fields = ['first_name', 'last_name', 'gender', 'age', 'phone_number', 'nin', 'blood_type', 'blood_sign', 'wilaya', 'commune']

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = models.PatientProfile
        fields = ['chronic_disease', 'chronic_disease_details', 'allergies', 'allergies_details', 'previous_surgeries', 'emergency_contact_name', 'emergency_contact_phone']

    def clean(self):
        cleaned_data = super().clean()
        chronic_disease = cleaned_data.get('chronic_disease')
        chronic_disease_details = cleaned_data.get('chronic_disease_details')
        allergies = cleaned_data.get('allergies')
        allergies_details = cleaned_data.get('allergies_details')

        if chronic_disease and not chronic_disease_details:
            self.add_error('chronic_disease_details', 'Please provide details of your chronic disease.')
        
        if allergies and not allergies_details:
            self.add_error('allergies_details', 'Please provide details of your allergies.')

        return cleaned_data

class DonorProfileForm(forms.ModelForm):
    class Meta:
        model = models.DonorProfile
        fields = ['chronic_disease', 'regular_medication', 'anemia', 'received_transfusion', 'donated_before', 'last_donation_date']

    def clean(self):
        cleaned_data = super().clean()
        donated_before = cleaned_data.get('donated_before')
        last_donation_date = cleaned_data.get('last_donation_date')

        if donated_before and not last_donation_date:
            self.add_error('last_donation_date', 'Please provide the date of your last donation.')

        return cleaned_data
