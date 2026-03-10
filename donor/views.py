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

# Donor signup has been moved to the unified signup flow in blood/views.py


def donor_dashboard_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    dict={
        'requestpending': bmodels.BloodRequest.objects.filter(request_by_donor=donor_profile, status='Pending').count(),
        'requestapproved': bmodels.BloodRequest.objects.filter(request_by_donor=donor_profile, status='Approved').count(),
        'requestmade': bmodels.BloodRequest.objects.filter(request_by_donor=donor_profile).count(),
        'requestrejected': bmodels.BloodRequest.objects.filter(request_by_donor=donor_profile, status='Rejected').count(),
    }
    return render(request,'donor/donor_dashboard.html',context=dict)


def donate_blood_view(request):
    donation_form=forms.DonationForm()
    if request.method=='POST':
        donation_form=forms.DonationForm(request.POST)
        if donation_form.is_valid():
            blood_donate=donation_form.save(commit=False)
            blood_donate.bloodgroup=donation_form.cleaned_data['bloodgroup']
            donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
            blood_donate.donor=donor_profile
            blood_donate.save()
            return HttpResponseRedirect('donation-history')  
    return render(request,'donor/donate_blood.html',{'donation_form':donation_form})

def donation_history_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    donations=models.BloodDonate.objects.filter(donor=donor_profile)
    return render(request,'donor/donation_history.html',{'donations':donations})

def make_request_view(request):
    request_form=bforms.RequestForm()
    if request.method=='POST':
        request_form=bforms.RequestForm(request.POST)
        if request_form.is_valid():
            blood_request=request_form.save(commit=False)
            blood_request.bloodgroup=request_form.cleaned_data['bloodgroup']
            donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
            blood_request.request_by_donor=donor_profile
            blood_request.save()
            return HttpResponseRedirect('request-history')  
    return render(request,'donor/makerequest.html',{'request_form':request_form})

def request_history_view(request):
    donor_profile = bmodels.DonorProfile.objects.get(app_user__user=request.user)
    blood_request=bmodels.BloodRequest.objects.filter(request_by_donor=donor_profile)
    return render(request,'donor/request_history.html',{'blood_request':blood_request})
