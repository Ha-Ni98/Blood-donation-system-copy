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
