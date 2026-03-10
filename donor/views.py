from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from blood import models as bmodels
from . import forms

# Donor signup has been moved to the unified signup flow in blood/views.py

@login_required
def donor_dashboard_view(request):
    try:
        donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    except bmodels.DonorProfile.DoesNotExist:
        return redirect('/')

    app_user = donor_profile.app_user
    
    # Active Request
    active_request = bmodels.DonationRequest.objects.filter(
        donor=donor_profile, 
        status__in=['pending', 'approved']
    ).first()

    # Eligibility logic
    is_eligible = donor_profile.is_eligible
    ineligible_reason = None

    if not is_eligible:
        ineligible_reason = _("Marked ineligible by administrator.")
    else:
        has_active_tsp = bmodels.TransfusionSafetyPeriod.objects.filter(
            donor=donor_profile, ends_at__gt=timezone.now()
        ).exists()
        if has_active_tsp:
            is_eligible = False
            ineligible_reason = _("Recent required safety period.")
        elif hasattr(app_user, 'patientprofile'):
            has_active_br = bmodels.BloodRequest.objects.filter(
                patient=app_user.patientprofile, status__in=['pending', 'approved']
            ).exists()
            if has_active_br:
                is_eligible = False
                ineligible_reason = _("Active blood request as a patient.")

    # Stat cards
    all_requests = bmodels.DonationRequest.objects.filter(donor=donor_profile)
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
        'blood_group': f"{app_user.blood_type}{app_user.blood_sign}",
        'active_request': active_request,
        'is_eligible': is_eligible,
        'ineligible_reason': ineligible_reason,
        'stats': stats,
    }
    
    return render(request, 'donor/donor_dashboard.html', context)

@login_required
def submit_donation_request_view(request):
    try:
        donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    except bmodels.DonorProfile.DoesNotExist:
        return redirect('/')

    app_user = donor_profile.app_user

    # Eligibility Checks
    if not donor_profile.is_eligible:
        messages.warning(request, _("You are currently not eligible to donate blood."))
        return redirect('donor-dashboard')

    if hasattr(app_user, 'patientprofile'):
        has_active_br = bmodels.BloodRequest.objects.filter(
            patient=app_user.patientprofile,
            status__in=['pending', 'approved']
        ).exists()
        if has_active_br:
            messages.warning(request, _("You cannot donate because you have an active blood request."))
            return redirect('donor-dashboard')

    has_active_dr = bmodels.DonationRequest.objects.filter(
        donor=donor_profile,
        status__in=['pending', 'approved']
    ).exists()
    if has_active_dr:
        messages.warning(request, _("You already have an active donation request."))
        return redirect('donor-dashboard')

    has_active_tsp = bmodels.TransfusionSafetyPeriod.objects.filter(
        donor=donor_profile,
        ends_at__gt=timezone.now()
    ).exists()
    if has_active_tsp:
        messages.warning(request, _("You cannot donate because you received a transfusion less than 6 months ago."))
        return redirect('donor-dashboard')

    if request.method == 'POST':
        form = forms.DonationRequestForm(request.POST, gender=app_user.gender)
        if form.is_valid():
            donation_request = form.save(commit=False)
            donation_request.donor = donor_profile
            donation_request.status = 'pending'
            donation_request.save()
            messages.success(request, _("Your donation request has been submitted."))
            return redirect('donor-dashboard')
    else:
        form = forms.DonationRequestForm(gender=app_user.gender)

    context = {
        'form': form,
        'full_name': f"{app_user.first_name} {app_user.last_name}",
        'blood_group': f"{app_user.blood_type}{app_user.blood_sign}",
        'age': app_user.age,
        'last_donation_date': donor_profile.last_donation_date,
        'is_female': app_user.gender == 'F'
    }
    return render(request, 'donor/donation_request_form.html', context)

@login_required
def donation_history_view(request):
    # Stubbed in Sprint 1 — will be fully implemented in a later Sprint
    return redirect('donor-dashboard')
