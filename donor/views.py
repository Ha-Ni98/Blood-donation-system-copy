from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from blood import models as bmodels
from . import forms

# Donor signup has been moved to the unified signup flow in blood/views.py

@login_required
def donor_dashboard_view(request):
    donor_profile = bmodels.DonorProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not donor_profile:
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
    next_eligible_date = None

    if not is_eligible:
        ineligible_reason = _("Marked ineligible by administrator.")
    elif app_user.age < 18:
        is_eligible = False
        ineligible_reason = _("You are under 18 years old.")
    elif donor_profile.chronic_disease:
        is_eligible = False
        ineligible_reason = _("You have a chronic disease.")
    elif donor_profile.anemia:
        is_eligible = False
        ineligible_reason = _("You have a history of anemia.")
    elif donor_profile.last_donation_date and donor_profile.last_donation_date > timezone.now().date() - timedelta(days=90):
        is_eligible = False
        days_since = (timezone.now().date() - donor_profile.last_donation_date).days
        days_left = 90 - days_since
        next_eligible_date = donor_profile.last_donation_date + timedelta(days=90)
        ineligible_reason = _("Last donation was {0} days ago. Please wait {1} more days.").format(days_since, days_left)
    else:
        has_active_tsp = bmodels.TransfusionSafetyPeriod.objects.filter(
            donor=donor_profile, ends_at__gt=timezone.now()
        ).exists()
        if has_active_tsp:
            is_eligible = False
            ineligible_reason = _("Recent required safety period.")
        else:
            patient_profile = app_user.patient_profiles.order_by('-created_at').first()
            if patient_profile:
                has_active_br = bmodels.BloodRequest.objects.filter(
                    patient=patient_profile, status__in=['pending', 'approved']
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
        'next_eligible_date': next_eligible_date,
        'stats': stats,
    }
    
    return render(request, 'donor/donor_dashboard.html', context)

@login_required
def submit_donation_request_view(request):
    donor_profile = bmodels.DonorProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not donor_profile:
        return redirect('/')

    app_user = donor_profile.app_user

    # Eligibility Checks
    if not donor_profile.is_eligible:
        messages.warning(request, _("You are currently not eligible to donate blood."))
        return redirect('donor-dashboard')

    if app_user.age < 18:
        messages.warning(request, _("You cannot donate because you are under 18 years old."))
        return redirect('donor-dashboard')

    if donor_profile.chronic_disease:
        messages.warning(request, _("You cannot donate because you have a chronic disease."))
        return redirect('donor-dashboard')

    if donor_profile.anemia:
        messages.warning(request, _("You cannot donate because you have anemia."))
        return redirect('donor-dashboard')

    if donor_profile.last_donation_date:
        ninety_days_ago = timezone.now().date() - timedelta(days=90)
        if donor_profile.last_donation_date > ninety_days_ago:
            messages.warning(request, _("You cannot donate because your last donation was less than 3 months ago."))
            return redirect('donor-dashboard')

    patient_profile = app_user.patient_profiles.order_by('-created_at').first()
    if patient_profile:
        has_active_br = bmodels.BloodRequest.objects.filter(
            patient=patient_profile,
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
            # Point 2: Additional Submission Validation Checks
            reason = None
            if form.cleaned_data.get('transfusion_last_6_months'):
                reason = _("you received a transfusion in the last 6 months")
            elif form.cleaned_data.get('surgery_last_6_months'):
                reason = _("you had surgery in the last 6 months")
            elif form.cleaned_data.get('has_anemia'):
                reason = _("you have anemia")
            elif app_user.gender == 'F' and (form.cleaned_data.get('is_pregnant') or form.cleaned_data.get('is_breastfeeding')):
                reason = _("you are pregnant or breastfeeding")
            elif form.cleaned_data.get('donated_last_3_months'):
                reason = _("you donated in the last 3 months")

            if reason:
                messages.error(request, _("Your donation request cannot be submitted because {0}.").format(reason))
                return render(request, 'donor/donation_request_form.html', {
                    'form': form,
                    'full_name': f"{app_user.first_name} {app_user.last_name}",
                    'blood_group': f"{app_user.blood_type}{app_user.blood_sign}",
                    'date_of_birth': app_user.date_of_birth,
                    'age': app_user.age,
                    'last_donation_date': donor_profile.last_donation_date,
                    'is_female': app_user.gender == 'F'
                })

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
        'date_of_birth': app_user.date_of_birth,
        'age': app_user.age,
        'last_donation_date': donor_profile.last_donation_date,
        'is_female': app_user.gender == 'F'
    }
    return render(request, 'donor/donation_request_form.html', context)

from django.db import transaction

@login_required
def cancel_donation_request_view(request, pk):
    donor_profile = bmodels.DonorProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not donor_profile:
        messages.error(request, _("Donor profile not found."))
        return redirect('donor-dashboard')

    try:
        donation_request = bmodels.DonationRequest.objects.get(id=pk, donor=donor_profile)
    except bmodels.DonationRequest.DoesNotExist:
        messages.error(request, _("Donation request not found or unauthorized."))
        return redirect('donor-dashboard')

    if request.method == 'POST':
        if donation_request.status in ['pending', 'approved']:
            with transaction.atomic():
                donation_request.status = 'cancelled_by_user'
                
                # Handle cascade if linked to a BloodRequest
                if donation_request.blood_request:
                    blood_req = donation_request.blood_request
                    blood_req.status = 'pending'
                    blood_req.save()
                    
                    # Unlink
                    donation_request.blood_request = None
                    
                    # Notify patient
                    bmodels.Notification.objects.create(
                        recipient=blood_req.patient.app_user,
                        title=_("Donation Cancelled"),
                        message=_("A donor cancelled their donation. Your blood request is now pending again.")
                    )
                    
                donation_request.save()
                messages.success(request, _("Your donation request has been cancelled."))
        else:
            messages.error(request, _("Only pending or approved requests can be cancelled."))
    else:
        messages.error(request, _("Invalid request method."))
        
    return redirect('donor-dashboard')

@login_required
def donation_history_view(request):
    donor_profile = bmodels.DonorProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not donor_profile:
        messages.error(request, _('Donor profile not found.'))
        return redirect('home')

    donations = bmodels.DonationRequest.objects.filter(donor=donor_profile).order_by('-created_at')
    
    context = {
        'donations': donations,
        'app_user': donor_profile.app_user
    }
    return render(request, 'donor/donation_history.html', context)

@login_required
def donor_notifications_view(request):
    try:
        app_user = bmodels.AppUser.objects.get(user=request.user)
    except bmodels.AppUser.DoesNotExist:
        return redirect('/')

    # Mark all unread notifications as read
    bmodels.Notification.objects.filter(recipient=app_user, is_read=False).update(is_read=True)

    # Fetch all notifications for the user
    notifications = bmodels.Notification.objects.filter(recipient=app_user).order_by('-created_at')

    context = {
        'notifications': notifications,
        'app_user': app_user
    }
    return render(request, 'donor/notifications.html', context)
