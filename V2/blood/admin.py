from django.contrib import admin

from .models import (
    Wilaya, Commune, BloodType, BloodStock, AppUser,
    BloodRequest, Notification, DonationRequest,
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


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'blood_type', 'units_needed', 'urgency', 'status', 'created_at', 'expires_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__user__email')
    list_filter = ('status', 'urgency', 'blood_type', 'wilaya')
    readonly_fields = ('created_at', 'updated_at', 'expires_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at', 'expires_at')
    search_fields = ('recipient__first_name', 'recipient__last_name', 'title', 'message')
    list_filter = ('is_read',)
    readonly_fields = ('created_at', 'expires_at')


@admin.register(DonationRequest)
class DonationRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'user__user__email')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
