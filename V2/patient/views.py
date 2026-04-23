from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from blood import models as bmodels
from blood import forms as bforms
from blood.models import ACTIVE_STATUSES

# Patient signup has been moved to the unified signup flow in blood/views.py


@login_required(login_url='login')
def patient_dashboard_view(request):
    app_user = request.user.app_user
    
    # Verify user is a patient
    if app_user.profil_type != 'Patient':
        messages.error(request, _('You do not have a patient profile.'))
        return redirect('home')

    # Active request: first Pending or Approved request (at most one exists per spec §4.5)
    active_request = bmodels.BloodRequest.objects.filter(
        user=app_user, status__in=list(ACTIVE_STATUSES)
    ).first()
    
    # Check if user has donor history (for banner display)
    has_donor_history = bmodels.DonationRequest.objects.filter(user=app_user).exists()

    context = {
        'app_user': app_user,
        'blood_type': app_user.blood_type,
        'active_request': active_request,
        'has_donor_history': has_donor_history,
        # Stat counts for all relevant statuses
        'requestmade': bmodels.BloodRequest.objects.filter(user=app_user).count(),
        'requestpending': bmodels.BloodRequest.objects.filter(user=app_user, status='pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.filter(user=app_user, status='approved').count(),
        'requestcompleted': bmodels.BloodRequest.objects.filter(user=app_user, status='completed').count(),
        'requestrejected': bmodels.BloodRequest.objects.filter(user=app_user, status='rejected').count(),
        'requestcancelled': bmodels.BloodRequest.objects.filter(
            user=app_user, status__in=['cancelled_by_user', 'cancelled_by_admin']
        ).count(),
        'requestexpired': bmodels.BloodRequest.objects.filter(user=app_user, status='expired').count(),
    }
    return render(request, 'patient/patient_dashboard.html', context=context)



@login_required(login_url='login')
def make_request_view(request):
    """
    Blood request creation view.
    Enforces:
      - Duplicate prevention: block if patient already has an active request (Spec §4.5)
      - Cross-profile blocking: block if user has active DonationRequest (Spec §7.1)
    Auto-fills read-only patient info from AppUser in context.
    Pre-fills Wilaya/Commune from AppUser as form initial.
    """
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Patient':
        messages.error(request, _('You do not have a patient profile.'))
        return redirect('home')

    # --- Rule 1: Duplicate prevention (Spec §4.5) ---
    has_active_request = bmodels.BloodRequest.objects.filter(
        user=app_user, status__in=list(ACTIVE_STATUSES)
    ).exists()
    if has_active_request:
        messages.warning(request, _('You already have an active blood request.'))
        return redirect('patient-dashboard')

    # --- Rule 2: Cross-profile blocking (Spec §7.1) ---
    # Check for active DonationRequests
    has_active_donation = bmodels.DonationRequest.objects.filter(
        user=app_user, status__in=['pending', 'approved']
    ).exists()
    if has_active_donation:
        messages.warning(
            request,
            _('You cannot request blood because you have an active donation request.')
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
            blood_request.user = app_user
            # status defaults to 'pending' via model default
            blood_request.save()
            # expires_at computed in BloodRequest.save()
            messages.success(request, _('Your blood request has been submitted.'))
            return redirect('patient-dashboard')
    else:
        form = bforms.BloodRequestForm(initial=initial)

    # Auto-fill context (read-only in template — Spec §4.1)
    context = {
        'form': form,
        'full_name': f"{app_user.first_name} {app_user.last_name}",
        'blood_type': app_user.blood_type,
        'date_of_birth': app_user.date_of_birth,
        'age': app_user.age,
    }
    return render(request, 'patient/blood_request_form.html', context)


@login_required(login_url='login')
def my_request_view(request):
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Patient':
        messages.error(request, _('You do not have a patient profile.'))
        return redirect('home')
        
    blood_request = bmodels.BloodRequest.objects.filter(
        user=app_user
    ).order_by('-created_at')
    return render(request, 'patient/my_request.html', {'blood_request': blood_request})


@login_required(login_url='login')
def cancel_request_view(request, pk):
    """
    Patient cancels their own blood request.
    - POST only (CSRF protected)
    - Ownership enforced: user must own the request
    - Only Pending or Approved statuses can be cancelled (Spec §4.4)
    - If Approved + linked DonationRequest exists: cascade cancel + notify donor
    """
    if request.method != 'POST':
        return redirect('my-request')

    app_user = request.user.app_user
    
    if app_user.profil_type != 'Patient':
        messages.error(request, _('You do not have a patient profile.'))
        return redirect('home')

    try:
        blood_request = bmodels.BloodRequest.objects.get(pk=pk, user=app_user)
    except bmodels.BloodRequest.DoesNotExist:
        messages.error(request, _('Blood request not found.'))
        return redirect('my-request')

    # Only Pending or Approved can be cancelled (Spec §4.4)
    if blood_request.status not in list(ACTIVE_STATUSES):
        messages.error(request, _('This request cannot be cancelled.'))
        return redirect('my-request')

    # Cascade: if Approved and linked DonationRequest exists — Spec §4.4
    if blood_request.status == 'approved':
        try:
            donation_req = blood_request.donation_requests.first()
            if donation_req:
                donation_req.status = 'cancelled_by_admin'
                donation_req.save()
                # Notify the donor
                bmodels.Notification.objects.create(
                    recipient=donation_req.user,
                    title=_('Donation Request Cancelled'),
                    message=_(
                        'The blood request you were matched with has been cancelled by the patient. '
                        'Your donation request has been cancelled.'
                    ),
                )
        except Exception:
            pass  # No linked DonationRequest — nothing to cascade

    blood_request.status = 'cancelled_by_user'
    blood_request.save()

    messages.success(request, _('Your request has been cancelled.'))
    return redirect('my-request')


@login_required(login_url='login')
def notifications_view(request):
    """
    Displays all notifications for the current patient.
    Marks all unread notifications as read on page load (Spec §8.3).
    """
    app_user = request.user.app_user
    
    if app_user.profil_type != 'Patient':
        messages.error(request, _('You do not have a patient profile.'))
        return redirect('home')

    # Bulk-mark unread as read before fetching (single UPDATE — efficient)
    bmodels.Notification.objects.filter(recipient=app_user, is_read=False).update(is_read=True)

    notifications = bmodels.Notification.objects.filter(
        recipient=app_user
    ).order_by('-created_at')

    return render(request, 'patient/notifications.html', {'notifications': notifications})
