from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum,Q
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from . import forms, models

def home_view(request):
    x=models.Stock.objects.all()
    print(x)
    if len(x)==0:
        blood1=models.Stock()
        blood1.bloodgroup="A+"
        blood1.save()

        blood2=models.Stock()
        blood2.bloodgroup="A-"
        blood2.save()

        blood3=models.Stock()
        blood3.bloodgroup="B+"
        blood3.save()        

        blood4=models.Stock()
        blood4.bloodgroup="B-"
        blood4.save()

        blood5=models.Stock()
        blood5.bloodgroup="AB+"
        blood5.save()

        blood6=models.Stock()
        blood6.bloodgroup="AB-"
        blood6.save()

        blood7=models.Stock()
        blood7.bloodgroup="O+"
        blood7.save()

        blood8=models.Stock()
        blood8.bloodgroup="O-"
        blood8.save()

    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')  
    return render(request,'blood/index.html')

def afterlogin_view(request):
    if hasattr(request.user, 'app_user'):
        app_user = request.user.app_user
        if hasattr(app_user, 'donorprofile') and hasattr(app_user, 'patientprofile'):
            return redirect('donor-dashboard')
        elif hasattr(app_user, 'donorprofile'):
            return redirect('donor-dashboard')
        elif hasattr(app_user, 'patientprofile'):
            return redirect('patient-dashboard')
        else:
            return redirect('admin-dashboard')
    else:
        return redirect('admin-dashboard')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')
        
    if request.method == 'POST':
        form = forms.LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Welcome back!')
                return redirect('afterlogin')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = forms.LoginForm()
    return render(request, 'blood/login.html', {'form': form})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')

    user_form = forms.SignupUserForm()
    app_user_form = forms.SignupAppUserForm()

    if request.method == 'POST':
        user_form = forms.SignupUserForm(request.POST)
        app_user_form = forms.SignupAppUserForm(request.POST)

        if user_form.is_valid() and app_user_form.is_valid():
            request.session['pending_registration'] = {
                'user': user_form.cleaned_data,
                'app_user': app_user_form.cleaned_data
            }
            # Add wilaya/commune IDs for reconstruction logic
            request.session['pending_registration']['app_user']['wilaya_id'] = app_user_form.cleaned_data['wilaya'].id
            request.session['pending_registration']['app_user']['commune_id'] = app_user_form.cleaned_data['commune'].id
            
            # Form cleaned_data contains unserializable Model instances, let's clean them out 
            del request.session['pending_registration']['app_user']['wilaya']
            del request.session['pending_registration']['app_user']['commune']

            return redirect('choose-profile') # View built in next sprint

    return render(request, 'blood/signup.html', {
        'user_form': user_form,
        'app_user_form': app_user_form
    })

def communes_api(request):
    wilaya_id = request.GET.get('wilaya_id')
    communes = models.Commune.objects.filter(wilaya_id=wilaya_id).order_by('name')
    return JsonResponse(list(communes.values('id', 'name')), safe=False)

def choose_profile_view(request):
    # If not logged in and no pending registration, redirect to home
    if not request.user.is_authenticated and 'pending_registration' not in request.session:
        return redirect('home')
    return render(request, 'blood/choose_profile.html')

def create_patient_profile_view(request):
    if request.method == 'POST':
        form = forms.PatientProfileForm(request.POST)
        if form.is_valid():
            if 'pending_registration' in request.session:
                # Flow: New User Registration
                session_data = request.session['pending_registration']
                
                try:
                    with transaction.atomic():
                        # Create User
                        user = User.objects.create_user(
                            username=session_data['user']['username'],
                            password=session_data['user']['password']
                        )
                        
                        # Reconstruct Wilaya and Commune
                        wilaya = models.Wilaya.objects.get(id=session_data['app_user']['wilaya_id'])
                        commune = models.Commune.objects.get(id=session_data['app_user']['commune_id'])
                        
                        # Create AppUser
                        app_user_data = session_data['app_user'].copy()
                        del app_user_data['wilaya_id']
                        del app_user_data['commune_id']
                        app_user_data.pop('terms', None)
                        
                        app_user = models.AppUser.objects.create(
                            user=user,
                            wilaya=wilaya,
                            commune=commune,
                            **app_user_data
                        )
                        
                        # Create PatientProfile
                        patient_profile = form.save(commit=False)
                        patient_profile.app_user = app_user
                        patient_profile.save()
                        
                        # Set Groups
                        my_patient_group = Group.objects.get_or_create(name='PATIENT')
                        my_patient_group[0].user_set.add(user)
                        
                    # Clean session and login
                    if 'pending_registration' in request.session:
                        del request.session['pending_registration']
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, 'Account created successfully.')
                    messages.success(request, 'Patient Profile created successfully.')
                    return redirect('patient-dashboard')
                        
                except Exception as e:
                    messages.error(request, f'An error occurred: {str(e)}')
            else:
                messages.error(request, 'No pending registration found.')
                return redirect('signup')
    else:
        form = forms.PatientProfileForm()
        
    return render(request, 'blood/create_patient_profile.html', {'form': form})

def create_donor_profile_view(request):
    if request.method == 'POST':
        form = forms.DonorProfileForm(request.POST)
        if form.is_valid():
            if 'pending_registration' in request.session:
                # Flow: New User Registration
                session_data = request.session['pending_registration']
                
                try:
                    with transaction.atomic():
                        # Create User
                        user = User.objects.create_user(
                            username=session_data['user']['username'],
                            password=session_data['user']['password']
                        )
                        
                        # Reconstruct Wilaya and Commune
                        wilaya = models.Wilaya.objects.get(id=session_data['app_user']['wilaya_id'])
                        commune = models.Commune.objects.get(id=session_data['app_user']['commune_id'])
                        
                        # Create AppUser
                        app_user_data = session_data['app_user'].copy()
                        del app_user_data['wilaya_id']
                        del app_user_data['commune_id']
                        app_user_data.pop('terms', None)
                        
                        app_user = models.AppUser.objects.create(
                            user=user,
                            wilaya=wilaya,
                            commune=commune,
                            **app_user_data
                        )
                        
                        # Create DonorProfile
                        donor_profile = form.save(commit=False)
                        donor_profile.app_user = app_user
                        donor_profile.save()
                        
                        # Set Groups
                        my_donor_group = Group.objects.get_or_create(name='DONOR')
                        my_donor_group[0].user_set.add(user)
                        
                    # Clean session and login
                    if 'pending_registration' in request.session:
                        del request.session['pending_registration']
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, 'Account created successfully.')
                    messages.success(request, 'Donor Profile created successfully.')
                    return redirect('donor-dashboard')
                        
                except Exception as e:
                    messages.error(request, f'An error occurred: {str(e)}')
            else:
                messages.error(request, 'No pending registration found.')
                return redirect('signup')
    else:
        form = forms.DonorProfileForm()
        
    return render(request, 'blood/create_donor_profile.html', {'form': form})

@login_required(login_url='adminlogin')
def create_donor_profile_from_patient_view(request):
    app_user = getattr(request.user, 'app_user', None)
    if not app_user:
        return redirect('home')

    if hasattr(app_user, 'donorprofile'):
        messages.info(request, "You already have a Donor profile.")
        return redirect('donor-dashboard')

    if request.method == 'POST':
        form = forms.DonorProfileForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                donor_profile = form.save(commit=False)
                donor_profile.app_user = app_user
                donor_profile.save()

                donor_group, _ = Group.objects.get_or_create(name='DONOR')
                donor_group.user_set.add(request.user)

            messages.success(request, "Donor profile created successfully.")
            return redirect('donor-dashboard')
    else:
        form = forms.DonorProfileForm()

    return render(request, 'blood/create_donor_profile.html', {'form': form})

@login_required(login_url='adminlogin')
def create_patient_profile_from_donor_view(request):
    app_user = getattr(request.user, 'app_user', None)
    if not app_user:
        return redirect('home')

    if hasattr(app_user, 'patientprofile'):
        messages.info(request, "You already have a Patient profile.")
        return redirect('patient-dashboard')

    if request.method == 'POST':
        form = forms.PatientProfileForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                patient_profile = form.save(commit=False)
                patient_profile.app_user = app_user
                patient_profile.save()

                patient_group, _ = Group.objects.get_or_create(name='PATIENT')
                patient_group.user_set.add(request.user)

            messages.success(request, "Patient profile created successfully.")
            return redirect('patient-dashboard')
    else:
        form = forms.PatientProfileForm()

    return render(request, 'blood/create_patient_profile.html', {'form': form})

@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    totalunit=models.Stock.objects.aggregate(Sum('unit'))
    dict={

        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
        'totaldonors':models.DonorProfile.objects.all().count(),
        'totalbloodunit':totalunit['unit__sum'],
        'totalrequest':models.BloodRequest.objects.all().count(),
        'totalapprovedrequest':models.BloodRequest.objects.all().filter(status='approved').count()
    }
    return render(request,'blood/admin_dashboard.html',context=dict)

@login_required(login_url='adminlogin')
def admin_blood_view(request):
    dict={
        'bloodForm':forms.BloodForm(),
        'A1':models.Stock.objects.get(bloodgroup="A+"),
        'A2':models.Stock.objects.get(bloodgroup="A-"),
        'B1':models.Stock.objects.get(bloodgroup="B+"),
        'B2':models.Stock.objects.get(bloodgroup="B-"),
        'AB1':models.Stock.objects.get(bloodgroup="AB+"),
        'AB2':models.Stock.objects.get(bloodgroup="AB-"),
        'O1':models.Stock.objects.get(bloodgroup="O+"),
        'O2':models.Stock.objects.get(bloodgroup="O-"),
    }
    if request.method=='POST':
        bloodForm=forms.BloodForm(request.POST)
        if bloodForm.is_valid() :        
            bloodgroup=bloodForm.cleaned_data['bloodgroup']
            stock=models.Stock.objects.get(bloodgroup=bloodgroup)
            stock.unit=bloodForm.cleaned_data['unit']
            stock.save()
        return HttpResponseRedirect('admin-blood')
    return render(request,'blood/admin_blood.html',context=dict)


@login_required(login_url='adminlogin')
def admin_donor_view(request):
    donors=models.DonorProfile.objects.all()
    return render(request,'blood/admin_donor.html',{'donors':donors})

@login_required(login_url='adminlogin')
def update_donor_view(request,pk):
    # This view will be rebuilt or disabled as part of the phase since
    # donor updates must go through AppUser unifying views. 
    # For now, redirecting to admin-donor to prevent errors.
    return redirect('admin-donor')

@login_required(login_url='adminlogin')
def delete_donor_view(request,pk):
    donor=models.DonorProfile.objects.get(id=pk)
    user=donor.app_user.user
    user.delete()
    return HttpResponseRedirect('/admin-donor')

@login_required(login_url='adminlogin')
def admin_patient_view(request):
    patients=models.PatientProfile.objects.all()
    return render(request,'blood/admin_patient.html',{'patients':patients})


@login_required(login_url='adminlogin')
def update_patient_view(request,pk):
    # This view will be rebuilt or disabled as part of the phase since
    # patient updates must go through AppUser unifying views. 
    # For now, redirecting to admin-patient to prevent errors.
    return redirect('admin-patient')

@login_required(login_url='adminlogin')
def delete_patient_view(request,pk):
    patient=models.PatientProfile.objects.get(id=pk)
    user=patient.app_user.user
    user.delete()
    return HttpResponseRedirect('/admin-patient')

@login_required(login_url='adminlogin')
def admin_request_view(request):
    requests=models.BloodRequest.objects.all().filter(status='pending')
    return render(request,'blood/admin_request.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_request_history_view(request):
    requests=models.BloodRequest.objects.all().exclude(status='pending')
    return render(request,'blood/admin_request_history.html',{'requests':requests})

@login_required(login_url='adminlogin')
def admin_donation_view(request):
    # Stubbed — legacy BloodDonate model references removed.
    # Will be rebuilt when DonationRequest views are implemented (Phase C).
    return render(request,'blood/admin_donation.html',{'donations': []})

@login_required(login_url='adminlogin')
def update_approve_status_view(request, pk):
    """Pending → Approved. Notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status in models.TERMINAL_STATUSES:
        messages.error(request, f'Cannot approve: request is already {req.status}.')
        return HttpResponseRedirect('/admin-request')
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be approved.')
        return HttpResponseRedirect('/admin-request')
    req.status = 'approved'
    req.save()
    models.Notification.objects.create(
        recipient=req.patient.app_user,
        title='Blood Request Approved',
        message=f'Your blood request for {req.blood_type}{req.blood_sign} has been approved.',
    )
    messages.success(request, 'Blood request approved.')
    return HttpResponseRedirect('/admin-request')


@login_required(login_url='adminlogin')
def update_reject_status_view(request, pk):
    """Pending → Rejected. Notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status in models.TERMINAL_STATUSES:
        messages.error(request, f'Cannot reject: request is already {req.status}.')
        return HttpResponseRedirect('/admin-request')
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be rejected.')
        return HttpResponseRedirect('/admin-request')
    req.status = 'rejected'
    req.save()
    models.Notification.objects.create(
        recipient=req.patient.app_user,
        title='Blood Request Rejected',
        message=f'Your blood request for {req.blood_type}{req.blood_sign} has been rejected.',
    )
    messages.success(request, 'Blood request rejected.')
    return HttpResponseRedirect('/admin-request')


@login_required(login_url='adminlogin')
def complete_blood_request_view(request, pk):
    """Approved → Completed. Creates TransfusionSafetyPeriod, sets donor ineligible, notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status in models.TERMINAL_STATUSES:
        messages.error(request, f'Cannot complete: request is already {req.status}.')
        return HttpResponseRedirect('/admin-request-history')
    if req.status != 'approved':
        messages.error(request, 'Only approved requests can be marked as completed.')
        return HttpResponseRedirect('/admin-request-history')
    req.status = 'completed'
    req.save()
    # Create TransfusionSafetyPeriod if a donor is linked via DonationRequest
    try:
        donation_req = req.donation_request
        donor_profile = donation_req.donor
        models.TransfusionSafetyPeriod.objects.create(
            donor=donor_profile,
            blood_request=req,
            started_at=date.today(),
        )
        donor_profile.is_eligible = False
        donor_profile.save()
    except models.DonationRequest.DoesNotExist:
        pass  # No linked donor — no safety period needed
    models.Notification.objects.create(
        recipient=req.patient.app_user,
        title='Blood Request Completed',
        message=f'Your blood request for {req.blood_type}{req.blood_sign} has been completed.',
    )
    messages.success(request, 'Blood request marked as completed.')
    return HttpResponseRedirect('/admin-request-history')


@login_required(login_url='adminlogin')
def admin_cancel_blood_request_view(request, pk):
    """Any non-terminal → Cancelled by Admin. Cascades to DonationRequest. Notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status in models.TERMINAL_STATUSES:
        messages.error(request, f'Cannot cancel: request is already {req.status}.')
        return HttpResponseRedirect('/admin-request')
    # Cascade to linked DonationRequest if exists
    try:
        donation_req = req.donation_request
        donation_req.status = 'cancelled_by_admin'
        donation_req.save()
        models.Notification.objects.create(
            recipient=donation_req.donor.app_user,
            title='Donation Request Cancelled',
            message='Your donation request has been cancelled by the admin.',
        )
    except models.DonationRequest.DoesNotExist:
        pass
    req.status = 'cancelled_by_admin'
    req.save()
    models.Notification.objects.create(
        recipient=req.patient.app_user,
        title='Blood Request Cancelled',
        message=f'Your blood request for {req.blood_type}{req.blood_sign} has been cancelled by the admin.',
    )
    messages.success(request, 'Blood request cancelled by admin.')
    return HttpResponseRedirect('/admin-request')

@login_required(login_url='adminlogin')
def approve_donation_view(request,pk):
    # Stubbed — legacy BloodDonate model references removed.
    # Will be rebuilt when DonationRequest views are implemented (Phase C).
    return HttpResponseRedirect('/admin-donation')

@login_required(login_url='adminlogin')
def reject_donation_view(request,pk):
    # Stubbed — legacy BloodDonate model references removed.
    # Will be rebuilt when DonationRequest views are implemented (Phase C).
    return HttpResponseRedirect('/admin-donation')