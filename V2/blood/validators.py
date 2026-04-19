from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re

def validate_nin(value):
    """
    Validates the Algerian National Identification Number (NIN).
    Must be exactly 18 digits, numeric only.
    """
    if not re.match(r'^\d{18}$', str(value)):
        raise ValidationError(
            _('NIN must be exactly 18 digits long.'),
            params={'value': value},
        )


def validate_phone_number(value):
    """
    Validates an Algerian phone number.
    Accepts:
      - Local format:         0XXXXXXXXX  (10 digits, starts with 0)
      - International format: +213XXXXXXXXX (starts with +213, followed by 9 digits)
    """
    pattern = r'^(0\d{9}|\+213\d{9})$'
    if not re.match(pattern, str(value)):
        raise ValidationError(
            _('Enter a valid Algerian phone number (e.g. 0551234567 or +213551234567).'),
            params={'value': value},
        )
