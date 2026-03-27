from django import forms
from django.utils.translation import gettext_lazy as _
from blood.models import DonationRequest
from django.core.exceptions import ValidationError

# Donor user/profile forms have been removed. 
# Registration is now handled by unified forms in blood/forms.py using AppUser and DonorProfile.

class DonationRequestForm(forms.ModelForm):
    # We redefine boolean fields to have custom labels and enforce that confirmations are True.
    # We use CheckboxInput or Select based on UI preference. We'll use RadioSelect with choices for yes/no.
    
    BOOL_CHOICES = [
        (True, _('Yes')),
        (False, _('No'))
    ]

    donated_last_3_months = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Donated blood in the last 3 months?")
    )
    transfusion_last_6_months = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Received a blood transfusion in the last 6 months?")
    )
    surgery_last_6_months = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Had surgery in the last 6 months?")
    )
    has_fever = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Currently have fever, infection, or flu?")
    )
    on_medication = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Currently taking medication?")
    )
    has_anemia = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Suffer from anemia?")
    )

    is_pregnant = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Are you pregnant?"), required=False
    )
    is_breastfeeding = forms.TypedChoiceField(
        choices=BOOL_CHOICES, widget=forms.RadioSelect, coerce=lambda x: x == 'True',
        label=_("Are you breastfeeding?"), required=False
    )

    confirmed_accurate = forms.BooleanField(
        required=True,
        label=_("I confirm the accuracy of this information"),
        error_messages={'required': _('You must confirm the accuracy of this information.')}
    )
    confirmed_understands = forms.BooleanField(
        required=True,
        label=_("I understand that providing false information may disqualify me"),
        error_messages={'required': _('You must acknowledge this before submitting.')}
    )

    class Meta:
        model = DonationRequest
        fields = [
            'donated_last_3_months', 'transfusion_last_6_months', 'surgery_last_6_months',
            'has_fever', 'on_medication', 'has_anemia',
            'is_pregnant', 'is_breastfeeding',
            'confirmed_accurate', 'confirmed_understands'
        ]

    def __init__(self, *args, **kwargs):
        self.gender = kwargs.pop('gender', None)
        super().__init__(*args, **kwargs)
        if self.gender != 'F':
            self.fields.pop('is_pregnant', None)
            self.fields.pop('is_breastfeeding', None)
        else:
            self.fields['is_pregnant'].required = True
            self.fields['is_breastfeeding'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if self.gender != 'F':
            cleaned_data['is_pregnant'] = None
            cleaned_data['is_breastfeeding'] = None
        
        # Enforce both checkboxes
        if not cleaned_data.get('confirmed_accurate') or not cleaned_data.get('confirmed_understands'):
            raise ValidationError(_("You must confirm both checkboxes at the bottom."))
            
        return cleaned_data
