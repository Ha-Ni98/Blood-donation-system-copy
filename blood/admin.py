from django.contrib import admin

from .models import Wilaya, Commune, AppUser, PatientProfile, DonorProfile

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

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'masked_nin', 'blood_type', 'blood_sign')
    search_fields = ('user__email', 'first_name', 'last_name', 'nin', 'phone_number')
    list_filter = ('blood_type', 'blood_sign', 'gender', 'wilaya')
    
    # Exclude nin from edit forms to enforce write-once visually in admin layer
    # (Though save() method protects it at the model layer)
    readonly_fields = ('nin', 'created_at')

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
