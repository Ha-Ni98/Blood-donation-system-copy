from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum, Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User
from blood import forms as bforms
from blood import models as bmodels

# Patient signup has been moved to the unified signup flow in blood/views.py

def patient_dashboard_view(request):
    patient_profile = bmodels.PatientProfile.objects.get(app_user__user=request.user)
    dict={
        'requestpending': bmodels.BloodRequest.objects.filter(request_by_patient=patient_profile, status='Pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.filter(request_by_patient=patient_profile, status='Approved').count(),
        'requestmade': bmodels.BloodRequest.objects.filter(request_by_patient=patient_profile).count(),
        'requestrejected': bmodels.BloodRequest.objects.filter(request_by_patient=patient_profile, status='Rejected').count(),
    }
   
    return render(request,'patient/patient_dashboard.html',context=dict)

def make_request_view(request):
    request_form=bforms.RequestForm()
    if request.method=='POST':
        request_form=bforms.RequestForm(request.POST)
        if request_form.is_valid():
            blood_request=request_form.save(commit=False)
            blood_request.bloodgroup=request_form.cleaned_data['bloodgroup']
            patient_profile = bmodels.PatientProfile.objects.get(app_user__user=request.user)
            blood_request.request_by_patient=patient_profile
            blood_request.save()
            return HttpResponseRedirect('my-request')  
    return render(request,'patient/makerequest.html',{'request_form':request_form})

def my_request_view(request):
    patient_profile = bmodels.PatientProfile.objects.get(app_user__user=request.user)
    blood_request=bmodels.BloodRequest.objects.filter(request_by_patient=patient_profile)
    return render(request,'patient/my_request.html',{'blood_request':blood_request})
