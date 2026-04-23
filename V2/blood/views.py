from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum, Q
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .decorators import admin_required, terminal_status_guard
from django.conf import settings
from datetime import date, timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'blood/index.html')

def afterlogin_view(request):
    if hasattr(request.user, 'app_user'):
        app_user = request.user.app_user
        if app_user.profil_type == 'Donor':
            return redirect('donor-dashboard')
        elif app_user.profil_type == 'Patient':
            return redirect('patient-dashboard')
        else:
            return redirect('home')
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
                messages.success(request, _('Welcome back!'))
                return redirect('afterlogin')
            else:
                messages.error(request, _('Invalid email or password.'))
        else:
            messages.error(request, _('Invalid email or password.'))
    else:
        form = forms.LoginForm()
    return render(request, 'blood/login.html', {'form': form})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('afterlogin')

    # Handle "go back" navigation (GET with go_to_step)
    go_to_step = request.GET.get('go_to_step')
    if go_to_step and request.method == 'GET':
        step = int(go_to_step)
        if step == 1 and 'reg_step1' in request.session:
            data = request.session['reg_step1'].copy()
            data['wilaya'] = data.get('wilaya_id')
            data['commune'] = data.get('commune_id')
            form1 = forms.RegisterStep1Form(initial=data)
            return render(request, 'blood/signup.html', {'step': 1, 'form1': form1})
        elif step == 2 and 'reg_step2' in request.session:
            data = request.session['reg_step2'].copy()
            data['blood_type'] = data.get('blood_type_id')
            # Deserialize date strings for form initial data
            if data.get('last_donation_date'):
                data['last_donation_date'] = date.fromisoformat(data['last_donation_date'])
            if data.get('last_transfusion_date'):
                data['last_transfusion_date'] = date.fromisoformat(data['last_transfusion_date'])
            form2 = forms.RegisterStep2Form(initial=data)
            return render(request, 'blood/signup.html', {'step': 2, 'form2': form2})

    if request.method == 'POST':
        step = int(request.POST.get('step', 1))

        if step == 1:
            form1 = forms.RegisterStep1Form(request.POST)
            if form1.is_valid():
                data = form1.cleaned_data.copy()
                data['date_of_birth'] = data['date_of_birth'].isoformat()
                data['wilaya_id'] = data['wilaya'].id
                data['commune_id'] = data['commune'].id
                del data['wilaya']
                del data['commune']
                request.session['reg_step1'] = data
                return render(request, 'blood/signup.html', {'step': 2, 'form2': forms.RegisterStep2Form()})
            return render(request, 'blood/signup.html', {'step': 1, 'form1': form1})

        elif step == 2:
            form2 = forms.RegisterStep2Form(request.POST)
            if form2.is_valid():
                data = form2.cleaned_data.copy()
                data['blood_type_id'] = data['blood_type'].id
                del data['blood_type']
                # Serialize date objects for session storage
                if data.get('last_donation_date'):
                    data['last_donation_date'] = data['last_donation_date'].isoformat()
                if data.get('last_transfusion_date'):
                    data['last_transfusion_date'] = data['last_transfusion_date'].isoformat()
                request.session['reg_step2'] = data
                return render(request, 'blood/signup.html', {'step': 3, 'form3': forms.RegisterStep3Form()})
            return render(request, 'blood/signup.html', {'step': 2, 'form2': form2})

        elif step == 3:
            form3 = forms.RegisterStep3Form(request.POST)
            if form3.is_valid():
                step1 = request.session.get('reg_step1')
                step2 = request.session.get('reg_step2')
                if not step1 or not step2:
                    return redirect('signup')
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=step1['email'],
                            email=step1['email'],
                            password=step1['password']
                        )
                        models.AppUser.objects.create(
                            user=user,
                            first_name=step1['first_name'],
                            last_name=step1['last_name'],
                            gender=step1['gender'],
                            date_of_birth=date.fromisoformat(step1['date_of_birth']),
                            phone_number=step1['phone_number'],
                            nin=step1['nin'],
                            blood_type=models.BloodType.objects.get(id=step2['blood_type_id']),
                            last_donation_date=step2.get('last_donation_date') or None,
                            last_transfusion_date=step2.get('last_transfusion_date') or None,
                            profil_type=form3.cleaned_data['profil_type'],
                            wilaya=models.Wilaya.objects.get(id=step1['wilaya_id']),
                            commune=models.Commune.objects.get(id=step1['commune_id']),
                        )
                    request.session.pop('reg_step1', None)
                    request.session.pop('reg_step2', None)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, _('Account created successfully.'))
                    return redirect('afterlogin')
                except Exception:
                    messages.error(request, _('Registration failed. Please try again.'))
                    return redirect('signup')
            return render(request, 'blood/signup.html', {'step': 3, 'form3': form3})
    else:
        form1 = forms.RegisterStep1Form()

    return render(request, 'blood/signup.html', {'step': 1, 'form1': form1})


def communes_api(request):
    wilaya_id = request.GET.get('wilaya_id')
    communes = models.Commune.objects.filter(wilaya_id=wilaya_id).order_by('name')
    return JsonResponse(list(communes.values('id', 'name')), safe=False)

@login_required(login_url='adminlogin')
def create_donor_profile_from_patient_view(request):
    """
    Allow a patient to create a donor profile by updating profil_type.
    Validates no active blood requests before allowing the switch.
    """
    app_user = getattr(request.user, 'app_user', None)
    if not app_user:
        return redirect('home')

    # Check for active blood requests (block switch if exists)
    has_active_br = models.BloodRequest.objects.filter(
        user=app_user,
        status__in=['pending', 'approved']
    ).exists()
    if has_active_br:
        messages.warning(request, _('You cannot switch to Donor because you have an active blood request.'))
        return redirect('patient-dashboard')

    if request.method == 'POST':
        with transaction.atomic():
            app_user.profil_type = 'Donor'
            app_user.save()

            donor_group, __ = Group.objects.get_or_create(name='DONOR')
            donor_group.user_set.add(request.user)

        messages.success(request, _('Donor profile created successfully.'))
        return redirect('donor-dashboard')

    return render(request, 'blood/create_donor_profile.html', {'app_user': app_user})

@login_required(login_url='adminlogin')
def create_patient_profile_from_donor_view(request):
    """
    Allow a donor to create a patient profile by updating profil_type.
    Validates no active donation requests before allowing the switch.
    """
    app_user = getattr(request.user, 'app_user', None)
    if not app_user:
        return redirect('home')

    # Check for active donation requests (block switch if exists)
    has_active_dr = models.DonationRequest.objects.filter(
        user=app_user,
        status__in=['pending', 'approved']
    ).exists()
    if has_active_dr:
        messages.warning(request, _('You cannot switch to Patient because you have an active donation request.'))
        return redirect('donor-dashboard')

    if request.method == 'POST':
        with transaction.atomic():
            app_user.profil_type = 'Patient'
            app_user.save()

            patient_group, __ = Group.objects.get_or_create(name='PATIENT')
            patient_group.user_set.add(request.user)

        messages.success(request, _('Patient profile created successfully.'))
        return redirect('patient-dashboard')

    return render(request, 'blood/create_patient_profile.html', {'app_user': app_user})

@admin_required(login_url='adminlogin')
def admin_dashboard_view(request):
    br_data = request.GET if 'btn_br_filter' in request.GET else {'status': 'pending'}
    dr_data = request.GET if 'btn_dr_filter' in request.GET else {'status': 'pending'}

    br_form = forms.AdminBloodRequestFilterForm(br_data)
    dr_form = forms.AdminDonationRequestFilterForm(dr_data)

    br_qs = models.BloodRequest.objects.select_related('patient__app_user', 'wilaya', 'commune').order_by('-created_at')
    dr_qs = models.DonationRequest.objects.select_related('donor__app_user').order_by('-created_at')

    if br_form.is_valid():
        if br_form.cleaned_data.get('status'):
            br_qs = br_qs.filter(status=br_form.cleaned_data['status'])
        if br_form.cleaned_data.get('urgency'):
            br_qs = br_qs.filter(urgency=br_form.cleaned_data['urgency'])
        if br_form.cleaned_data.get('blood_type'):
            br_qs = br_qs.filter(blood_type=br_form.cleaned_data['blood_type'])
        if br_form.cleaned_data.get('blood_sign'):
            br_qs = br_qs.filter(blood_sign=br_form.cleaned_data['blood_sign'])
        if br_form.cleaned_data.get('wilaya'):
            br_qs = br_qs.filter(wilaya=br_form.cleaned_data['wilaya'])

    if dr_form.is_valid():
        if dr_form.cleaned_data.get('status'):
            dr_qs = dr_qs.filter(status=dr_form.cleaned_data['status'])

    context = {
        'br_form': br_form,
        'dr_form': dr_form,
        'blood_requests': br_qs[:50],
        'donation_requests': dr_qs[:50],
    }
    return render(request, 'blood/admin_requests_dashboard.html', context)

@admin_required(login_url='adminlogin')
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


@admin_required(login_url='adminlogin')
def admin_user_management_view(request):
    """
    Displays all users (AppUser.user.is_active toggling).
    Handles POST requests to toggle the is_active status of a user.
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_id and action in ['activate', 'deactivate']:
            try:
                user = User.objects.get(id=user_id)
                # Prevent admin from deactivating themselves
                if user == request.user:
                    messages.error(request, "You cannot deactivate your own account.")
                else:
                    user.is_active = (action == 'activate')
                    user.save()
                    status_str = "activated" if user.is_active else "deactivated"
                    messages.success(request, f"User {user.username} has been {status_str}.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        return redirect('admin-user-management')

    # GET: List all AppUsers with their related auth User
    users = models.AppUser.objects.select_related('user', 'wilaya', 'commune').all()
    return render(request, 'blood/admin_user_management.html', {'users': users})

@admin_required(login_url='adminlogin')
def admin_donor_eligibility_view(request):
    """
    Displays all donors.
    Handles POST requests to toggle the is_eligible status of a donor.
    """
    if request.method == 'POST':
        donor_id = request.POST.get('donor_id')
        action = request.POST.get('action')
        
        if donor_id and action in ['mark_eligible', 'mark_ineligible']:
            try:
                donor = models.DonorProfile.objects.get(id=donor_id)
                donor.is_eligible = (action == 'mark_eligible')
                donor.save()
                
                status_str = "eligible" if donor.is_eligible else "ineligible"
                messages.success(request, f"Donor {donor.app_user.first_name} {donor.app_user.last_name} marked as {status_str}.")
            except models.DonorProfile.DoesNotExist:
                messages.error(request, "Donor not found.")
        return redirect('admin-donor-eligibility')

    # GET: List all DonorProfiles
    donors = models.DonorProfile.objects.select_related('app_user').all()
    return render(request, 'blood/admin_donor_eligibility.html', {'donors': donors})

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def update_reject_status_view(request, pk):
    """Pending → Rejected. Notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be rejected.')
        return redirect('admin-dashboard')
    
    req.status = 'rejected'
    req.save()
    
    models.Notification.objects.create(
        recipient=req.patient.app_user,
        title='Blood Request Rejected',
        message=f'Your blood request status has been updated to Rejected.',
    )
    messages.success(request, 'Request has been rejected successfully.')
    return redirect('admin-dashboard')


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def complete_blood_request_view(request, pk):
    """Approved → Completed. Atomic. Creates TransfusionSafetyPeriod, sets donor ineligible, notifies patient/donor."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status != 'approved':
        messages.error(request, 'Only approved requests can be marked as completed.')
        return redirect('admin-dashboard')
    
    with transaction.atomic():
        req.status = 'completed'
        req.save()
        
        # Cascade to linked DonationRequests
        donation_reqs = req.donation_requests.select_for_update().filter(status='approved')
        for donation_req in donation_reqs:
            donation_req.status = 'completed'
            donation_req.save()
            
            # Determine donor profile eligibility side effects (Spec §7.2)
            donor_profile = donation_req.donor
            models.TransfusionSafetyPeriod.objects.create(
                donor=donor_profile,
                blood_request=req,
                started_at=date.today(),
            )
            donor_profile.is_eligible = False
            donor_profile.last_donation_date = date.today()
            donor_profile.save()
            
            models.Notification.objects.create(
                recipient=donor_profile.app_user,
                title='Donation Completed',
                message='Your donation request status has been updated to Completed.',
            )
            
        models.Notification.objects.create(
            recipient=req.patient.app_user,
            title='Blood Request Completed',
            message=f'Your blood request status has been updated to Completed.',
        )
        
    messages.success(request, 'Request has been completed successfully.')
    return redirect('admin-dashboard')


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def admin_cancel_blood_request_view(request, pk):
    """Pending/Approved → Cancelled by Admin. Atomic. Cascades to DonationRequest. Notifies patient/donor."""
    req = models.BloodRequest.objects.get(id=pk)
    
    with transaction.atomic():
        # Cascade to linked DonationRequests if approved
        if req.status == 'approved':
            donation_reqs = req.donation_requests.select_for_update().filter(status__in=['pending', 'approved'])
            for donation_req in donation_reqs:
                donation_req.status = 'cancelled_by_admin'
                donation_req.save()
                
                models.Notification.objects.create(
                    recipient=donation_req.donor.app_user,
                    title='Donation Request Cancelled',
                    message="The patient's blood request was cancelled by the admin. Your donation request has been cancelled.",
                )
            
        req.status = 'cancelled_by_admin'
        req.save()
        
        models.Notification.objects.create(
            recipient=req.patient.app_user,
            title='Blood Request Cancelled',
            message=f'Your blood request status has been updated to Cancelled.',
        )
        
    messages.success(request, 'Request has been cancelled successfully.')
    return redirect('admin-dashboard')

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def approve_donation_view(request, pk):
    """Pending → Approved. Requires selecting an eligible pending BloodRequest. Atomic."""
    req = models.DonationRequest.objects.get(id=pk)
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be approved.')
        return redirect('admin-dashboard')
        
    # Get eligible pending blood requests (exact blood type match)
    eligible_blood_requests = models.BloodRequest.objects.filter(
        status='pending',
        blood_type=req.donor.app_user.blood_type,
        blood_sign=req.donor.app_user.blood_sign
    ).select_related('patient__app_user', 'wilaya', 'commune')
    
    if request.method == 'POST':
        blood_request_id = request.POST.get('blood_request_id')
        if not blood_request_id:
            messages.error(request, 'Please select a blood request.')
            return redirect('approve-donation', pk=pk)
            
        try:
            with transaction.atomic():
                blood_req = models.BloodRequest.objects.select_for_update().get(id=blood_request_id, status='pending')
                
                # Link and update statuses
                req.blood_request = blood_req
                req.status = 'approved'
                blood_req.status = 'approved'
                
                req.save()
                blood_req.save()
                
                # Notify Donor
                models.Notification.objects.create(
                    recipient=req.donor.app_user,
                    title='Donation Request Approved',
                    message='Your donation request status has been updated to Approved.',
                )
                
                # Notify Patient
                models.Notification.objects.create(
                    recipient=blood_req.patient.app_user,
                    title='Blood Request Approved',
                    message='Your blood request status has been updated to Approved.',
                )
                
            messages.success(request, 'Request has been approved successfully.')
            return redirect('admin-dashboard')
            
        except models.BloodRequest.DoesNotExist:
            messages.error(request, 'The selected blood request is no longer available.')
            return redirect('approve-donation', pk=pk)
            
    # GET: render selection form
    return render(request, 'blood/admin_approve_donation_request.html', {
        'req': req,
        'eligible_blood_requests': eligible_blood_requests
    })

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def update_approve_status_view(request, pk):
    """Pending → Approved. Requires selecting 1 or more eligible pending DonationRequests. Atomic."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be approved.')
        return redirect('admin-dashboard')
        
    # Get eligible pending donations (exact blood type match)
    eligible_donations = models.DonationRequest.objects.filter(
        status='pending',
        donor__app_user__blood_type=req.blood_type,
        donor__app_user__blood_sign=req.blood_sign
    ).select_related('donor__app_user')
    
    if request.method == 'POST':
        donation_ids = request.POST.getlist('donation_ids')
        if not donation_ids:
            messages.error(request, 'Please select at least one donor.')
            return redirect('update-approve-status', pk=pk)
            
        try:
            with transaction.atomic():
                # Lock the donation requests
                selected_donations = models.DonationRequest.objects.select_for_update().filter(
                    id__in=donation_ids, status='pending'
                )
                
                if len(selected_donations) != len(donation_ids):
                    messages.error(request, 'One or more selected donations are no longer available.')
                    return redirect('update-approve-status', pk=pk)

                # Link and update statuses
                for donation_req in selected_donations:
                    donation_req.blood_request = req
                    donation_req.status = 'approved'
                    donation_req.save()
                    
                    # Notify Donor
                    models.Notification.objects.create(
                        recipient=donation_req.donor.app_user,
                        title='Donation Request Approved',
                        message=f'Your donation request has been matched and Approved for a Blood Request.',
                    )

                req.status = 'approved'
                req.save()
                
                # Notify Patient
                models.Notification.objects.create(
                    recipient=req.patient.app_user,
                    title='Blood Request Approved',
                    message='Your blood request status has been updated to Approved and matched with donor(s).',
                )
                
            messages.success(request, 'Request has been approved successfully.')
            return redirect('admin-dashboard')
            
        except Exception as e:
            messages.error(request, 'An error occurred while approving the request.')
            return redirect('update-approve-status', pk=pk)
            
    # GET: render selection form
    return render(request, 'blood/admin_approve_blood_request.html', {
        'req': req,
        'eligible_donations': eligible_donations
    })

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def reject_donation_view(request,pk):
    """Pending → Rejected. Notifies donor."""
    req = models.DonationRequest.objects.get(id=pk)
    if req.status != 'pending':
        messages.error(request, 'Only pending requests can be rejected.')
        return redirect('admin-dashboard')
        
    req.status = 'rejected'
    req.save()
    
    models.Notification.objects.create(
        recipient=req.donor.app_user,
        title='Donation Request Rejected',
        message='Your donation request status has been updated to Rejected.',
    )
    messages.success(request, 'Request has been rejected successfully.')
    return redirect('admin-dashboard')

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def complete_donation_request_view(request, pk):
    """Approved → Completed. Notifies donor."""
    req = models.DonationRequest.objects.get(id=pk)
    if req.status != 'approved':
        messages.error(request, 'Only approved requests can be marked as completed.')
        return redirect('admin-dashboard')
        
    with transaction.atomic():
        req.status = 'completed'
        req.save()
        
        # Point 3: Update donor profile
        donor_profile = req.donor
        donor_profile.is_eligible = False
        donor_profile.last_donation_date = date.today()
        donor_profile.save()
    
    models.Notification.objects.create(
        recipient=req.donor.app_user,
        title='Donation Completed',
        message='Your donation request status has been updated to Completed.',
    )
    messages.success(request, 'Request has been completed successfully.')
    return redirect('admin-dashboard')

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def admin_cancel_donation_request_view(request, pk):
    """Pending/Approved → Cancelled by Admin. Atomic. Reverts linked BloodRequest. Notifies patient/donor."""
    req = models.DonationRequest.objects.get(id=pk)
    
    with transaction.atomic():
        req.status = 'cancelled_by_admin'
        
        # Unlink and revert BloodRequest if exists
        if req.blood_request:
            blood_req = req.blood_request
            blood_req.status = 'pending'
            req.blood_request = None
            blood_req.save()
            
            models.Notification.objects.create(
                recipient=blood_req.patient.app_user,
                title='Donor Request Cancelled',
                message="A donor's request was cancelled by the admin. Your blood request is now pending again.",
            )
            
        req.save()
        
        models.Notification.objects.create(
            recipient=req.donor.app_user,
            title='Donation Request Cancelled',
            message='Your donation request status has been updated to Cancelled by Admin.',
        )
        
    messages.success(request, 'Request has been cancelled successfully.')
    return redirect('admin-dashboard')