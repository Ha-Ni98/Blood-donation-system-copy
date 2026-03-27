from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from .validators import validate_nin, validate_phone_number


# --- Shared choice constants ---
BLOOD_TYPE_CHOICES = [
    ('A', 'A'),
    ('B', 'B'),
    ('AB', 'AB'),
    ('O', 'O'),
]

BLOOD_SIGN_CHOICES = [
    ('+', '+'),
    ('-', '-'),
]


class Wilaya(models.Model):
    code = models.CharField(max_length=4, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code}-{self.name}"


class Commune(models.Model):
    name = models.CharField(max_length=100)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.wilaya.name})"


class AppUser(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    BLOOD_TYPE_CHOICES = BLOOD_TYPE_CHOICES
    BLOOD_SIGN_CHOICES = BLOOD_SIGN_CHOICES

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_user')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20, validators=[validate_phone_number])
    nin = models.CharField(max_length=18, unique=True, validators=[validate_nin])
    blood_type = models.CharField(max_length=2, choices=BLOOD_TYPE_CHOICES)
    blood_sign = models.CharField(max_length=1, choices=BLOOD_SIGN_CHOICES)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.PROTECT)
    commune = models.ForeignKey(Commune, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Enforce NIN write-once
        if self.pk:
            original = AppUser.objects.get(pk=self.pk)
            self.nin = original.nin
        super().save(*args, **kwargs)

    @property
    def get_full_blood_group(self):
        """Returns the full blood group string (e.g., A+)"""
        return f"{self.blood_type}{self.blood_sign}"

    @property
    def masked_nin(self):
        """Returns the NIN masked, resolving to *************XXXXX"""
        if not self.nin or len(self.nin) != 18:
            return self.nin
        return "*" * 13 + self.nin[-5:]

    @property
    def age(self):
        """Computes current age from date_of_birth."""
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class PatientProfile(models.Model):
    app_user = models.OneToOneField(AppUser, on_delete=models.CASCADE)
    chronic_disease = models.BooleanField(default=False)
    chronic_disease_details = models.CharField(max_length=255, blank=True, null=True)
    allergies = models.BooleanField(default=False)
    allergies_details = models.CharField(max_length=255, blank=True, null=True)
    previous_surgeries = models.BooleanField(default=False)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Patient Profile: {self.app_user}"


class DonorProfile(models.Model):
    app_user = models.OneToOneField(AppUser, on_delete=models.CASCADE)
    chronic_disease = models.BooleanField(default=False)
    regular_medication = models.BooleanField(default=False)
    anemia = models.BooleanField(default=False)
    received_transfusion = models.BooleanField(default=False)
    donated_before = models.BooleanField(default=False)
    last_donation_date = models.DateField(blank=True, null=True)
    is_eligible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Donor Profile: {self.app_user}"


class Stock(models.Model):
    bloodgroup = models.CharField(max_length=10)
    unit = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.bloodgroup


# --- BloodRequest status constants ---
STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_COMPLETED = 'completed'
STATUS_REJECTED = 'rejected'
STATUS_CANCELLED_BY_USER = 'cancelled_by_user'
STATUS_CANCELLED_BY_ADMIN = 'cancelled_by_admin'
STATUS_EXPIRED = 'expired'

BLOOD_REQUEST_STATUS_CHOICES = [
    (STATUS_PENDING, 'Pending'),
    (STATUS_APPROVED, 'Approved'),
    (STATUS_COMPLETED, 'Completed'),
    (STATUS_REJECTED, 'Rejected'),
    (STATUS_CANCELLED_BY_USER, 'Cancelled by User'),
    (STATUS_CANCELLED_BY_ADMIN, 'Cancelled by Admin'),
    (STATUS_EXPIRED, 'Expired'),
]

# Terminal statuses cannot be changed once set (Spec §4.4)
TERMINAL_STATUSES = frozenset([
    STATUS_COMPLETED, STATUS_REJECTED,
    STATUS_CANCELLED_BY_USER, STATUS_CANCELLED_BY_ADMIN,
    STATUS_EXPIRED,
])

# Active statuses block new request creation (Spec §4.5)
ACTIVE_STATUSES = frozenset([STATUS_PENDING, STATUS_APPROVED])

URGENCY_CHOICES = [
    ('normal', 'Normal'),
    ('urgent', 'Urgent'),
    ('critical', 'Critical'),
]


class BloodRequest(models.Model):
    patient = models.ForeignKey(
        'PatientProfile', on_delete=models.CASCADE, related_name='blood_requests'
    )
    blood_type = models.CharField(max_length=2, choices=BLOOD_TYPE_CHOICES)
    blood_sign = models.CharField(max_length=1, choices=BLOOD_SIGN_CHOICES)
    units_needed = models.PositiveIntegerField()
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='normal')
    required_date = models.DateField()
    reason = models.TextField()
    recent_surgery = models.BooleanField(default=False)
    wilaya = models.ForeignKey(Wilaya, on_delete=models.PROTECT)
    commune = models.ForeignKey(Commune, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20, choices=BLOOD_REQUEST_STATUS_CHOICES, default=STATUS_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Computed on first save: min(required_date, created_at + 30 days)
    expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Compute expires_at only on first save (creation)
        if is_new and self.expires_at is None:
            # created_at is now set by auto_now_add after first save
            thirty_days = self.created_at + timedelta(days=30)
            # required_date is a date; convert to datetime for comparison
            required_dt = timezone.make_aware(
                timezone.datetime.combine(self.required_date, timezone.datetime.min.time())
            ) if timezone.is_naive(
                timezone.datetime.combine(self.required_date, timezone.datetime.min.time())
            ) else timezone.datetime.combine(self.required_date, timezone.datetime.min.time())
            self.expires_at = min(required_dt, thirty_days)
            # Save again to persist expires_at (only the expires_at field)
            BloodRequest.objects.filter(pk=self.pk).update(expires_at=self.expires_at)

    def __str__(self):
        return f"BloodRequest #{self.pk} - {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(models.Model):
    """
    In-app notification for an AppUser (patient or donor).
    Auto-expires 60 days after creation (cleaned by Celery — Sprint 9).
    """
    recipient = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Computed on first save: created_at + 60 days (Spec §8.3)
    expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=60)
            Notification.objects.filter(pk=self.pk).update(expires_at=self.expires_at)

    def __str__(self):
        return f"Notification → {self.recipient} — {self.title}"


# ---------------------------------------------------------------------------
# TransfusionSafetyPeriod
# ---------------------------------------------------------------------------

class TransfusionSafetyPeriod(models.Model):
    """
    Created when a BloodRequest is marked Completed and the patient also has
    a DonorProfile. Blocks that donor from donating for 6 months (Spec §7.2).
    """
    # OneToOne: one donor can only have one active safety period at a time
    donor = models.OneToOneField(
        DonorProfile, on_delete=models.CASCADE, related_name='transfusion_safety_period'
    )
    blood_request = models.ForeignKey(
        BloodRequest, on_delete=models.CASCADE, related_name='safety_periods'
    )
    started_at = models.DateTimeField()
    # Computed on save: started_at + 6 months
    ends_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.ends_at and self.started_at:
            # 6 months approximated as 183 days (Spec §7.2)
            self.ends_at = self.started_at + timedelta(days=183)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"SafetyPeriod: {self.donor} until {self.ends_at}"


# ---------------------------------------------------------------------------
# DonationRequest (stub — donor-facing views built in Phase C)
# ---------------------------------------------------------------------------

DONATION_REQUEST_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('completed', 'Completed'),
    ('rejected', 'Rejected'),
    ('cancelled_by_user', 'Cancelled by User'),
    ('cancelled_by_admin', 'Cancelled by Admin'),
]

DONATION_TERMINAL_STATUSES = frozenset([
    'completed', 'rejected', 'cancelled_by_user', 'cancelled_by_admin'
])

class DonationRequest(models.Model):
    """
    A donor's offer to donate blood, optionally linked to a BloodRequest.
    The donor-facing form and views for creating DonationRequests are Phase C scope.
    Only the model is created here so that BloodRequest.save() can reference it
    (via the OneToOne) and admin can link them.
    """
    donor = models.ForeignKey(
        DonorProfile, on_delete=models.CASCADE, related_name='donation_requests'
    )
    # Nullable — admin links this to a BloodRequest (Phase C/D admin action)
    blood_request = models.ForeignKey(
        BloodRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donation_requests',
    )

    # --- Health screening fields (Spec §9.1) ---
    donated_last_3_months = models.BooleanField(default=False)
    transfusion_last_6_months = models.BooleanField(default=False)
    surgery_last_6_months = models.BooleanField(default=False)
    has_fever = models.BooleanField(default=False)
    on_medication = models.BooleanField(default=False)
    has_anemia = models.BooleanField(default=False)
    # Female-only fields — nullable for male donors
    is_pregnant = models.BooleanField(null=True, blank=True)
    is_breastfeeding = models.BooleanField(null=True, blank=True)

    # --- Confirmation checkboxes (Spec §9.2) ---
    confirmed_accurate = models.BooleanField(default=False)
    confirmed_understands = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=DONATION_REQUEST_STATUS_CHOICES,
        default='pending',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DonationRequest #{self.pk} by {self.donor} — {self.get_status_display()}"