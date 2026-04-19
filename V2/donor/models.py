from django.db import models
from django.contrib.auth.models import User

# Legacy Donor and BloodDonate models have been removed in Phase C Sprint 1.
# Donor profiles are now tracked via `AppUser` and `DonorProfile` in the `blood` app,
# and donations are tracked via `DonationRequest` in the `blood` app.