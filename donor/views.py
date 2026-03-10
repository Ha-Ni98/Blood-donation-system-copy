from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from blood import models as bmodels

# Donor signup has been moved to the unified signup flow in blood/views.py

@login_required
def donor_dashboard_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    # Stubbed — donor dashboard stats will be refactored in Phase C Sprint 3.
    dict = {
        'requestpending': 0,
        'requestapproved': 0,
        'requestmade': 0,
        'requestrejected': 0,
    }
    return render(request, 'donor/donor_dashboard.html', context=dict)

@login_required
def donate_blood_view(request):
    # Stubbed in Sprint 1 — will be fully implemented as submit_donation_request_view in Sprint 2
    return redirect('donor-dashboard')

@login_required
def donation_history_view(request):
    # Stubbed in Sprint 1 — will be fully implemented in a later Sprint
    return redirect('donor-dashboard')
