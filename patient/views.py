from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from blood import models as bmodels
from blood import forms as bforms
from blood.models import ACTIVE_STATUSES

# Patient signup has been moved to the unified signup flow in blood/views.py


@login_required(login_url='login')
def patient_dashboard_view(request):
    patient_profile = bmodels.PatientProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not patient_profile:
        return redirect('home')
    app_user = patient_profile.app_user

    # Active request: first Pending or Approved request (at most one exists per spec §4.5)
    active_request = bmodels.BloodRequest.objects.filter(
        patient=patient_profile, status__in=list(ACTIVE_STATUSES)
    ).first()

    context = {
        'app_user': app_user,
        'patient_profile': patient_profile,
        'blood_group': f"{app_user.blood_type}{app_user.blood_sign}",
        'active_request': active_request,
        # Stat counts for all relevant statuses
        'requestmade': bmodels.BloodRequest.objects.filter(patient=patient_profile).count(),
        'requestpending': bmodels.BloodRequest.objects.filter(patient=patient_profile, status='pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.filter(patient=patient_profile, status='approved').count(),
        'requestcompleted': bmodels.BloodRequest.objects.filter(patient=patient_profile, status='completed').count(),
        'requestrejected': bmodels.BloodRequest.objects.filter(patient=patient_profile, status='rejected').count(),
        'requestcancelled': bmodels.BloodRequest.objects.filter(
            patient=patient_profile, status__in=['cancelled_by_user', 'cancelled_by_admin']
        ).count(),
        'requestexpired': bmodels.BloodRequest.objects.filter(patient=patient_profile, status='expired').count(),
    }
    return render(request, 'patient/patient_dashboard.html', context=context)



@login_required(login_url='login')
def make_request_view(request):
    """
    Blood request creation view.
    Enforces:
      - Duplicate prevention: block if patient already has an active request (Spec §4.5)
      - Cross-profile blocking: block if patient's DonorProfile has an active
        DonationRequest (Spec §7.1)
    Auto-fills read-only patient info from AppUser in context.
    Pre-fills Wilaya/Commune from AppUser as form initial.
    """
    patient_profile = bmodels.PatientProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not patient_profile:
        messages.error(request, 'Patient profile not found.')
        return redirect('home')

    app_user = patient_profile.app_user

    # --- Rule 1: Duplicate prevention (Spec §4.5) ---
    has_active_request = bmodels.BloodRequest.objects.filter(
        patient=patient_profile, status__in=list(ACTIVE_STATUSES)
    ).exists()
    if has_active_request:
        messages.warning(request, 'You already have an active blood request.')
        return redirect('patient-dashboard')

    # --- Rule 2: Cross-profile blocking (Spec §7.1) ---
    # If the patient also has a DonorProfile, check for active DonationRequests
    donor_profile = app_user.donor_profiles.order_by('-created_at').first()
    if donor_profile:
        has_active_donation = bmodels.DonationRequest.objects.filter(
            donor=donor_profile, status__in=['pending', 'approved']
        ).exists()
        if has_active_donation:
            messages.warning(
                request,
                'You cannot request blood because you have an active donation request.'
            )
            return redirect('patient-dashboard')

    # Pre-fill Wilaya and Commune from AppUser (editable by patient)
    initial = {
        'wilaya': app_user.wilaya,
        'commune': app_user.commune,
    }

    if request.method == 'POST':
        form = bforms.BloodRequestForm(request.POST, initial=initial)
        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.patient = patient_profile
            # status defaults to 'pending' via model default
            blood_request.save()
            # expires_at computed in BloodRequest.save()
            messages.success(request, 'Your blood request has been submitted.')
            return redirect('patient-dashboard')
    else:
        form = bforms.BloodRequestForm(initial=initial)

    # Auto-fill context (read-only in template — Spec §4.1)
    context = {
        'form': form,
        'full_name': f"{app_user.first_name} {app_user.last_name}",
        'blood_group': f"{app_user.blood_type}{app_user.blood_sign}",
        'date_of_birth': app_user.date_of_birth,
        'age': app_user.age,
    }
    return render(request, 'patient/blood_request_form.html', context)


@login_required(login_url='login')
def my_request_view(request):
    patient_profile = bmodels.PatientProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not patient_profile:
        return redirect('home')
    blood_request = bmodels.BloodRequest.objects.filter(
        patient=patient_profile
    ).order_by('-created_at')
    return render(request, 'patient/my_request.html', {'blood_request': blood_request})


@login_required(login_url='login')
def cancel_request_view(request, pk):
    """
    Patient cancels their own blood request.
    - POST only (CSRF protected)
    - Ownership enforced: patient must own the request
    - Only Pending or Approved statuses can be cancelled (Spec §4.4)
    - If Approved + linked DonationRequest exists: cascade cancel + notify donor
    """
    if request.method != 'POST':
        return redirect('my-request')

    patient_profile = bmodels.PatientProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not patient_profile:
        messages.error(request, 'Patient profile not found.')
        return redirect('home')

    try:
        blood_request = bmodels.BloodRequest.objects.get(pk=pk, patient=patient_profile)
    except bmodels.BloodRequest.DoesNotExist:
        messages.error(request, 'Blood request not found.')
        return redirect('my-request')

    # Only Pending or Approved can be cancelled (Spec §4.4)
    if blood_request.status not in list(ACTIVE_STATUSES):
        messages.error(request, 'This request cannot be cancelled.')
        return redirect('my-request')

    # Cascade: if Approved and linked DonationRequest exists — Spec §4.4
    if blood_request.status == 'approved':
        try:
            donation_req = blood_request.donation_request
            donation_req.status = 'cancelled_by_admin'
            donation_req.save()
            # Notify the donor
            bmodels.Notification.objects.create(
                recipient=donation_req.donor.app_user,
                title='Donation Request Cancelled',
                message=(
                    f'The blood request you were matched with has been cancelled by the patient. '
                    f'Your donation request has been cancelled.'
                ),
            )
        except bmodels.DonationRequest.DoesNotExist:
            pass  # No linked DonationRequest — nothing to cascade

    blood_request.status = 'cancelled_by_user'
    blood_request.save()

    messages.success(request, 'Your request has been cancelled.')
    return redirect('my-request')


@login_required(login_url='login')
def notifications_view(request):
    """
    Displays all notifications for the current patient.
    Marks all unread notifications as read on page load (Spec §8.3).
    """
    patient_profile = bmodels.PatientProfile.objects.filter(app_user__user=request.user).order_by('-created_at').first()
    if not patient_profile:
        messages.error(request, 'Patient profile not found.')
        return redirect('home')

    app_user = patient_profile.app_user

    # Bulk-mark unread as read before fetching (single UPDATE — efficient)
    bmodels.Notification.objects.filter(recipient=app_user, is_read=False).update(is_read=True)

    notifications = bmodels.Notification.objects.filter(
        recipient=app_user
    ).order_by('-created_at')

    return render(request, 'patient/notifications.html', {'notifications': notifications})
