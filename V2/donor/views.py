from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from blood import models as bmodels
from . import forms

# Donor signup has been moved to the unified signup flow in blood/views.py

def calculate_donor_eligibility(app_user):
    """
    Calculate donor eligibility based on AppUser fields.
    Returns: (is_eligible: bool, reason: str or None, next_date: date or None)
    """
    today = timezone.now().date()
    
    if app_user.age < 18:
        return False, _("You must be at least 18 years old to donate."), None
    
    if app_user.last_donation_date:
        donation_eligible_date = app_user.last_donation_date + timedelta(days=90)
        if today < donation_eligible_date:
            days_left = (donation_eligible_date - today).days
            return False, _("Last donation was recent. Please wait {0} more days.").format(days_left), donation_eligible_date
    
    if app_user.last_transfusion_date:
        transfusion_eligible_date = app_user.last_transfusion_date + timedelta(days=180)
        if today < transfusion_eligible_date:
            days_left = (transfusion_eligible_date - today).days
            return False, _("Recent transfusion. Please wait {0} more days.").format(days_left), transfusion_eligible_date
    
    return True, None, None


@login_required
def donor_dashboard_view(request):
    app_user = request.user.app_user
    
    # Verify user is a donor
    if app_user.profil_type != 'Donor':
        messages.error(request, _('You do not have a donor profile.'))
        return redirect('home')
    
    # Active Request
    active_request = bmodels.DonationRequest.objects.filter(
        user=app_user, 
        status__in=['pending', 'approved']
    ).first()
    
    # Check if user has patient history (for banner display)
    has_patient_history = bmodels.BloodRequest.objects.filter(user=app_user).exists()

    # Eligibility calculation from AppUser fields
    is_eligible, ineligible_reason, next_eligible_date = calculate_donor_eligibility(app_user)

    # Stat cards
    all_requests = bmodels.DonationRequest.objects.filter(user=app_user)
    stats = {
        'total': all_requests.count(),
        'pending': all_requests.filter(status='pending').count(),
        'approved': all_requests.filter(status='approved').count(),
        'completed': all_requests.filter(status='completed').count(),
        'rejected': all_requests.filter(status='rejected').count(),
        'cancelled': all_requests.filter(status='cancelled_by_user').count() + all_requests.filter(status='cancelled_by_admin').count(),
    }

    context = {
        'app_user': app_user,
        'blood_type': app_user.blood_type,
        'active_request': active_request,
        'has_patient_history': has_patient_history,
        'is_eligible': is_eligible,
        'ineligible_reason': ineligible_reason,
        'next_eligible_date': next_eligible_date,
        'stats': stats,
    }
    
    return render(request, 'donor/donor_dashboard.html', context)

@login_required
def submit_donation_request_view(request):
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Donor':
        messages.error(request, _('You do not have a donor profile.'))
        return redirect('home')

    # Eligibility Check from AppUser fields
    is_eligible, ineligible_reason, __ = calculate_donor_eligibility(app_user)
    if not is_eligible:
        messages.warning(request, ineligible_reason)
        return redirect('donor-dashboard')

    # Check for active donation request
    has_active_dr = bmodels.DonationRequest.objects.filter(
        user=app_user,
        status__in=['pending', 'approved']
    ).exists()
    if has_active_dr:
        messages.warning(request, _("You already have an active donation request."))
        return redirect('donor-dashboard')

    # Check for active blood request (cross-profile blocking)
    has_active_br = bmodels.BloodRequest.objects.filter(
        user=app_user,
        status__in=['pending', 'approved']
    ).exists()
    if has_active_br:
        messages.warning(request, _("You cannot donate because you have an active blood request."))
        return redirect('donor-dashboard')

    if request.method == 'POST':
        form = forms.DonationRequestForm(request.POST, gender=app_user.gender)
        if form.is_valid():
            # Check if donor is eligible based on screening
            if not form.is_eligible():
                messages.warning(request, _("Sorry, you cannot perform a donation request."))
                return redirect('donor-dashboard')

            # All blocking answers are 'No' - save the donation request
            donation_request = form.save(commit=False)
            donation_request.user = app_user
            donation_request.status = 'pending'
            # had_surgery is saved regardless of answer
            donation_request.had_surgery = form.cleaned_data.get('surgery_last_6_months', False)
            donation_request.save()
            messages.success(request, _("You have successfully performed a donation request."))
            return redirect('donor-dashboard')
    else:
        form = forms.DonationRequestForm(gender=app_user.gender)

    context = {
        'form': form,
        'full_name': f"{app_user.first_name} {app_user.last_name}",
        'blood_type': app_user.blood_type,
        'date_of_birth': app_user.date_of_birth,
        'age': app_user.age,
        'is_female': app_user.gender == "female" or app_user.gender == "Female"
    }
    return render(request, 'donor/donation_request_form.html', context)

from django.db import transaction

@login_required
def cancel_donation_request_view(request, pk):
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Donor':
        messages.error(request, _("You do not have a donor profile."))
        return redirect('home')

    try:
        donation_request = bmodels.DonationRequest.objects.get(id=pk, user=app_user)
    except bmodels.DonationRequest.DoesNotExist:
        messages.error(request, _("Donation request not found or unauthorized."))
        return redirect('donor-dashboard')

    if request.method == 'POST':
        if donation_request.status in ['pending', 'approved']:
            with transaction.atomic():
                donation_request.status = 'cancelled_by_user'
                donation_request.save()
                messages.success(request, _("Your donation request has been cancelled."))
        else:
            messages.error(request, _("Only pending or approved requests can be cancelled."))
    else:
        messages.error(request, _("Invalid request method."))
        
    return redirect('donor-dashboard')

@login_required
def donation_history_view(request):
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Donor':
        messages.error(request, _('You do not have a donor profile.'))
        return redirect('home')

    donations = bmodels.DonationRequest.objects.filter(user=app_user).order_by('-created_at')
    
    context = {
        'donations': donations,
        'app_user': app_user
    }
    return render(request, 'donor/donation_history.html', context)

@login_required
def donor_notifications_view(request):
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Donor':
        messages.error(request, _('You do not have a donor profile.'))
        return redirect('home')

    # Mark all unread notifications as read
    bmodels.Notification.objects.filter(recipient=app_user, is_read=False).update(is_read=True)

    # Fetch all notifications for the user
    notifications = bmodels.Notification.objects.filter(recipient=app_user).order_by('-created_at')

    context = {
        'notifications': notifications,
        'app_user': app_user
    }
    return render(request, 'donor/notifications.html', context)
