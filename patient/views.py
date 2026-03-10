from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from blood import models as bmodels

# Patient signup has been moved to the unified signup flow in blood/views.py


@login_required(login_url='login')
def patient_dashboard_view(request):
    patient_profile = bmodels.PatientProfile.objects.get(app_user__user=request.user)
    # Stubbed — uses new BloodRequest field names.
    # Full dashboard redesign in Sprint 5.
    dict = {
        'requestpending': bmodels.BloodRequest.objects.filter(
            patient=patient_profile, status='pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.filter(
            patient=patient_profile, status='approved').count(),
        'requestmade': bmodels.BloodRequest.objects.filter(
            patient=patient_profile).count(),
        'requestrejected': bmodels.BloodRequest.objects.filter(
            patient=patient_profile, status='rejected').count(),
    }
    return render(request, 'patient/patient_dashboard.html', context=dict)


@login_required(login_url='login')
def make_request_view(request):
    # Stubbed — legacy RequestForm removed. Full form/view in Sprint 3.
    messages.info(request, 'Blood request form is being upgraded.')
    return redirect('patient-dashboard')


@login_required(login_url='login')
def my_request_view(request):
    patient_profile = bmodels.PatientProfile.objects.get(app_user__user=request.user)
    # Uses new FK name 'patient' instead of legacy 'request_by_patient'
    blood_request = bmodels.BloodRequest.objects.filter(patient=patient_profile)
    return render(request, 'patient/my_request.html', {'blood_request': blood_request})
