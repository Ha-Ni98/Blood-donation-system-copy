from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .validators import validate_nin


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
        return f"{self.code} - {self.name}"


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
    age = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=20)
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
    def masked_nin(self):
        """Returns the NIN masked, resolving to *************XXXXX"""
        if not self.nin or len(self.nin) != 18:
            return self.nin
        return "*" * 13 + self.nin[-5:]

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