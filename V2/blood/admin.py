from django.contrib import admin

from .models import (
    Wilaya, Commune, BloodType, BloodStock, AppUser, PatientProfile, DonorProfile,
    BloodRequest, Notification, TransfusionSafetyPeriod, DonationRequest,
)


@admin.register(Wilaya)
class WilayaAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ('name', 'wilaya')
    search_fields = ('name', 'wilaya__name', 'wilaya__code')
    list_filter = ('wilaya',)


@admin.register(BloodType)
class BloodTypeAdmin(admin.ModelAdmin):
    list_display = ('blood_type', 'blood_sign')


@admin.register(BloodStock)
class BloodStockAdmin(admin.ModelAdmin):
    list_display = ('blood_type', 'units_available', 'updated_at')


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'masked_nin', 'blood_type', 'profil_type')
    search_fields = ('user__email', 'first_name', 'last_name', 'phone_number')
    list_filter = ('blood_type', 'profil_type', 'gender', 'wilaya')

    exclude = ('nin',)
    readonly_fields = ('masked_nin', 'created_at')


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('app_user', 'chronic_disease', 'allergies', 'previous_surgeries', 'created_at')
    search_fields = ('app_user__user__email', 'app_user__first_name', 'app_user__last_name', 'emergency_contact_name')
    list_filter = ('chronic_disease', 'allergies', 'previous_surgeries')
    readonly_fields = ('created_at',)


@admin.register(DonorProfile)
class DonorProfileAdmin(admin.ModelAdmin):
    list_display = ('app_user', 'is_eligible', 'donated_before', 'last_donation_date', 'created_at')
    search_fields = ('app_user__user__email', 'app_user__first_name', 'app_user__last_name')
    list_filter = ('is_eligible', 'donated_before', 'chronic_disease', 'anemia')
    readonly_fields = ('created_at',)


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'blood_type', 'blood_sign', 'units_needed', 'urgency', 'status', 'created_at', 'expires_at')
    search_fields = ('patient__app_user__first_name', 'patient__app_user__last_name')
    list_filter = ('status', 'urgency', 'blood_type', 'blood_sign', 'wilaya')
    readonly_fields = ('created_at', 'updated_at', 'expires_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at', 'expires_at')
    search_fields = ('recipient__first_name', 'recipient__last_name', 'title', 'message')
    list_filter = ('is_read',)
    readonly_fields = ('created_at', 'expires_at')


@admin.register(TransfusionSafetyPeriod)
class TransfusionSafetyPeriodAdmin(admin.ModelAdmin):
    list_display = ('donor', 'blood_request', 'started_at', 'ends_at')
    search_fields = ('donor__app_user__first_name', 'donor__app_user__last_name')
    readonly_fields = ('ends_at',)


@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'blood_request', 'status', 'created_at')
    search_fields = ('donor__app_user__first_name', 'donor__app_user__last_name')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
