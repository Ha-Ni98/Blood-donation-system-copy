from django.shortcuts import render, redirect
from . import forms, models
from django.contrib.auth.decorators import login_required
from blood import models as bmodels

# Donor signup has been moved to the unified signup flow in blood/views.py


def donor_dashboard_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    # Stubbed — donor dashboard stats will be refactored in Phase C.
    # BloodRequest no longer has request_by_donor FK; donors use DonationRequest.
    dict = {
        'requestpending': 0,
        'requestapproved': 0,
        'requestmade': 0,
        'requestrejected': 0,
    }
    return render(request, 'donor/donor_dashboard.html', context=dict)


def donate_blood_view(request):
    donation_form = forms.DonationForm()
    if request.method == 'POST':
        donation_form = forms.DonationForm(request.POST)
        if donation_form.is_valid():
            blood_donate = donation_form.save(commit=False)
            blood_donate.bloodgroup = donation_form.cleaned_data['bloodgroup']
            donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
            blood_donate.donor = donor_profile
            blood_donate.save()
            return redirect('donation-history')
    return render(request, 'donor/donate_blood.html', {'donation_form': donation_form})


def donation_history_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    donations = models.BloodDonate.objects.filter(donor=donor_profile)
    return render(request, 'donor/donation_history.html', {'donations': donations})


# make_request_view REMOVED — donors do not submit BloodRequests.
# DonationRequest views will be built in Phase C.

# request_history_view REMOVED — donors do not have BloodRequest history.
# DonationRequest history will be built in Phase C.
