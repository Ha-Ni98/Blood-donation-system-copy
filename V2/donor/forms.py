from django import forms
from django.utils.translation import gettext_lazy as _
from blood.models import DonationRequest
from django.core.exceptions import ValidationError

# Donor user/profile forms have been removed. 
# Registration is now handled by unified forms in blood/forms.py using AppUser and DonorProfile.

class DonationRequestForm(forms.ModelForm):
    """
    Health screening form. All questions are form-only fields.
    If any answer is 'Yes', the request is rejected with a notification.
    Only wilaya and commune are saved to the model.
    """
    
    BOOL_CHOICES = [
        (True, _('Yes')),
        (False, _('No'))
    ]

    # Health screening questions (form-only, not saved to model)
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
        fields = ['wilaya', 'commune']
        widgets = {
            'wilaya': forms.Select(attrs={'class': 'form-control'}),
            'commune': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.gender = kwargs.pop('gender', None)
        super().__init__(*args, **kwargs)
        # Make wilaya/commune required
        self.fields['wilaya'].required = True
        self.fields['commune'].required = True
        # Remove empty option for wilaya/commune
        self.fields['wilaya'].empty_label = None
        self.fields['commune'].empty_label = None
        
        if self.gender and self.gender.lower() != 'female':
            self.fields.pop('is_pregnant', None)
            self.fields.pop('is_breastfeeding', None)
        else:
            self.fields['is_pregnant'].required = True
            self.fields['is_breastfeeding'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if self.gender and self.gender.lower() != 'female':
            cleaned_data['is_pregnant'] = False
            cleaned_data['is_breastfeeding'] = False
        
        # Enforce both checkboxes
        if not cleaned_data.get('confirmed_accurate') or not cleaned_data.get('confirmed_understands'):
            raise ValidationError(_("You must confirm both checkboxes at the bottom."))
            
        return cleaned_data

    def is_eligible(self):
        """Returns True if donor is eligible, False otherwise."""
        cleaned_data = self.cleaned_data
        
        blocking_conditions = [
            cleaned_data.get('donated_last_3_months'),
            cleaned_data.get('transfusion_last_6_months'),
            cleaned_data.get('surgery_last_6_months'),
            cleaned_data.get('has_fever'),
            cleaned_data.get('on_medication'),
            cleaned_data.get('has_anemia'),
            cleaned_data.get('is_pregnant'),
            cleaned_data.get('is_breastfeeding'),
        ]
        
        return not any(blocking_conditions)
