from django import forms
from . import models
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .validators import validate_nin, validate_phone_number

class BloodRequestForm(forms.ModelForm):
    # Confirmation checkbox — not a model field, required by Spec §4.1
    confirmation = forms.BooleanField(
        required=True,
        label="I confirm the accuracy of this information",
        error_messages={'required': 'You must confirm the accuracy of this information.'},
    )

    class Meta:
        model = models.BloodRequest
        fields = [
            'blood_type', 'blood_sign', 'units_needed', 'urgency',
            'required_date', 'reason', 'recent_surgery', 'wilaya', 'commune',
        ]
        widgets = {
            'required_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_units_needed(self):
        value = self.cleaned_data.get('units_needed')
        if value is not None and value < 1:
            raise forms.ValidationError("Units needed must be at least 1.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        wilaya = cleaned_data.get('wilaya')
        commune = cleaned_data.get('commune')
        # Ensure commune belongs to the chosen wilaya
        if wilaya and commune and commune.wilaya != wilaya:
            self.add_error('commune', 'Selected commune does not belong to the chosen wilaya.')
        return cleaned_data



class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = _('Email')


class RegisterStep1Form(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        error_messages={'invalid': _('Enter a valid email address.')}
    )
    password = forms.CharField(widget=forms.PasswordInput(), label=_('Password'))
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label=_('Confirm Password'))
    first_name = forms.CharField(max_length=100, label=_('First Name'))
    last_name = forms.CharField(max_length=100, label=_('Last Name'))
    phone_number = forms.CharField(max_length=20, label=_('Phone Number'), validators=[validate_phone_number])
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label=_('Date of Birth'))
    gender = forms.ChoiceField(
        choices=[('', '---------'), ('male', _('Male')), ('female', _('Female'))],
        label=_('Gender')
    )
    nin = forms.CharField(max_length=18, label=_('National Identity Number (NIN)'), validators=[validate_nin])
    wilaya = forms.ModelChoiceField(queryset=models.Wilaya.objects.all(), label=_('Wilaya'))
    commune = forms.ModelChoiceField(queryset=models.Commune.objects.all(), label=_('Commune'))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError(_('A user with this email already exists.'))
        return email

    def clean_nin(self):
        nin = self.cleaned_data.get('nin')
        if models.AppUser.objects.filter(nin=nin).exists():
            raise forms.ValidationError(_('This NIN is already registered.'))
        return nin

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _('Password and Confirm Password do not match.'))
        return cleaned_data


class RegisterStep2Form(forms.Form):
    blood_type = forms.ModelChoiceField(queryset=models.BloodType.objects.all(), label=_('Blood Type'))
    donated_before = forms.BooleanField(required=False, label=_('Have you donated blood before?'))
    last_donation_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label=_('Last Donation Date')
    )
    received_transfusion = forms.BooleanField(required=False, label=_('Have you received a blood transfusion?'))
    last_transfusion_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label=_('Last Transfusion Date')
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('donated_before') and not cleaned_data.get('last_donation_date'):
            self.add_error('last_donation_date', _('Please provide the date of your last donation.'))
        if cleaned_data.get('received_transfusion') and not cleaned_data.get('last_transfusion_date'):
            self.add_error('last_transfusion_date', _('Please provide the date of your last transfusion.'))
        return cleaned_data


class RegisterStep3Form(forms.Form):
    profil_type = forms.ChoiceField(
        choices=[('Patient', _('Patient')), ('Donor', _('Donor'))],
        widget=forms.RadioSelect,
        label=_('Profile Type')
    )


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = models.PatientProfile
        fields = ['chronic_disease', 'chronic_disease_details', 'allergies', 'allergies_details', 'previous_surgeries']

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


class AdminBloodRequestFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + models.BLOOD_REQUEST_STATUS_CHOICES, required=False
    )
    urgency = forms.ChoiceField(
        choices=[('', 'All Urgencies')] + models.URGENCY_CHOICES, required=False
    )
    blood_type = forms.ChoiceField(
        choices=[('', 'All Types')] + models.BLOOD_TYPE_CHOICES, required=False
    )
    blood_sign = forms.ChoiceField(
        choices=[('', 'All Signs')] + models.BLOOD_SIGN_CHOICES, required=False
    )
    wilaya = forms.ModelChoiceField(
        queryset=models.Wilaya.objects.all(), empty_label='All Wilayas', required=False
    )


class AdminDonationRequestFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + models.DONATION_REQUEST_STATUS_CHOICES, required=False
    )

