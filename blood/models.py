from django.db import models
from django.contrib.auth.models import User
from .validators import validate_nin

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
    bloodgroup=models.CharField(max_length=10)
    unit=models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.bloodgroup

class BloodRequest(models.Model):
    request_by_patient=models.ForeignKey('PatientProfile',null=True,on_delete=models.CASCADE)
    request_by_donor=models.ForeignKey('DonorProfile',null=True,on_delete=models.CASCADE)
    patient_name=models.CharField(max_length=30)
    patient_age=models.PositiveIntegerField()
    reason=models.CharField(max_length=500)
    bloodgroup=models.CharField(max_length=10)
    unit=models.PositiveIntegerField(default=0)
    status=models.CharField(max_length=20,default="Pending")
    date=models.DateField(auto_now=True)
    def __str__(self):
        return self.bloodgroup

        