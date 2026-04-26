from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from .validators import validate_nin, validate_phone_number


# --- Shared choice constants ---
# Used by BloodRequest only. AppUser uses BloodType FK.
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


class BloodType(models.Model):
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
    blood_type = models.CharField(max_length=2, choices=BLOOD_TYPE_CHOICES)
    blood_sign = models.CharField(max_length=1, choices=BLOOD_SIGN_CHOICES)

    class Meta:
        unique_together = ('blood_type', 'blood_sign')

    def __str__(self):
        return f"{self.blood_type}{self.blood_sign}"


class BloodStock(models.Model):
    blood_type = models.ForeignKey(BloodType, on_delete=models.PROTECT)
    units_available = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.blood_type}: {self.units_available} units"


class AppUser(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    PROFIL_TYPE_CHOICES = [
        ('Patient', 'Patient'),
        ('Donor', 'Donor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_user')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20, validators=[validate_phone_number])
    nin = models.CharField(max_length=18, unique=True, validators=[validate_nin])
    blood_type = models.ForeignKey(BloodType, on_delete=models.PROTECT)
    profil_type = models.CharField(max_length=10, choices=PROFIL_TYPE_CHOICES)
    last_donation_date = models.DateField(blank=True, null=True)
    last_transfusion_date = models.DateField(blank=True, null=True)
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
        return str(self.blood_type)

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
    user = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name='blood_requests'
    )
    blood_type = models.ForeignKey(BloodType, on_delete=models.PROTECT)
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


class BloodAttribution(models.Model):
    blood_request = models.ForeignKey(
        BloodRequest, on_delete=models.CASCADE, related_name='attributions'
    )
    blood_type = models.ForeignKey(BloodType, on_delete=models.PROTECT)
    units_attributed = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('blood_request', 'blood_type')

    def __str__(self):
        return f"Attribution #{self.pk} — {self.blood_type} x{self.units_attributed} for Request #{self.blood_request_id}"


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
# DonationRequest
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
    A donor's offer to donate blood.
    """
    user = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name='donation_requests'
    )

    wilaya = models.ForeignKey(
        Wilaya, on_delete=models.SET_NULL, null=True, blank=True
    )
    commune = models.ForeignKey(
        Commune, on_delete=models.SET_NULL, null=True, blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=DONATION_REQUEST_STATUS_CHOICES,
        default='pending',
    )
    donation_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DonationRequest #{self.pk} by {self.user} — {self.get_status_display()}"