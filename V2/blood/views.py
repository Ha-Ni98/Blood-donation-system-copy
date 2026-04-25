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
from . import services

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
            data['blood_type'] = data.get('blood_type_id')
            form1 = forms.RegisterStep1Form(initial=data)
            return render(request, 'blood/signup.html', {'step': 1, 'form1': form1})

    if request.method == 'POST':
        step = int(request.POST.get('step', 1))

        if step == 1:
            form1 = forms.RegisterStep1Form(request.POST)
            if form1.is_valid():
                data = form1.cleaned_data.copy()
                data['date_of_birth'] = data['date_of_birth'].isoformat()
                data['wilaya_id'] = data['wilaya'].id
                data['commune_id'] = data['commune'].id
                data['blood_type_id'] = data['blood_type'].id
                del data['wilaya']
                del data['commune']
                del data['blood_type']
                request.session['reg_step1'] = data
                return render(request, 'blood/signup.html', {'step': 2, 'form2': forms.RegisterStep2Form()})
            return render(request, 'blood/signup.html', {'step': 1, 'form1': form1})

        elif step == 2:
            form2 = forms.RegisterStep2Form(request.POST)
            if form2.is_valid():
                step1 = request.session.get('reg_step1')
                if not step1:
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
                            blood_type=models.BloodType.objects.get(id=step1['blood_type_id']),
                            profil_type=form2.cleaned_data['profil_type'],
                            wilaya=models.Wilaya.objects.get(id=step1['wilaya_id']),
                            commune=models.Commune.objects.get(id=step1['commune_id']),
                        )
                    request.session.pop('reg_step1', None)
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request, _('Account created successfully.'))
                    return redirect('afterlogin')
                except Exception:
                    messages.error(request, _('Registration failed. Please try again.'))
                    return redirect('signup')
            return render(request, 'blood/signup.html', {'step': 2, 'form2': form2})
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
    # Aggregate counts
    total_users = models.AppUser.objects.count()
    total_completed_donations = models.DonationRequest.objects.filter(status='completed').count()
    total_completed_blood_requests = models.BloodRequest.objects.filter(status='completed').count()

    # Blood stock table data
    blood_stocks = models.BloodStock.objects.select_related('blood_type').order_by(
        'blood_type__blood_type', 'blood_type__blood_sign'
    )
    total_stock_units = blood_stocks.aggregate(total=Sum('units_available'))['total'] or 0

    # Pending counts
    pending_blood_requests_count = models.BloodRequest.objects.filter(status='pending').count()
    pending_donation_requests_count = models.DonationRequest.objects.filter(status='pending').count()

    context = {
        'total_users': total_users,
        'total_stock_units': total_stock_units,
        'total_completed_donations': total_completed_donations,
        'total_completed_blood_requests': total_completed_blood_requests,
        'blood_stocks': blood_stocks,
        'pending_blood_requests_count': pending_blood_requests_count,
        'pending_donation_requests_count': pending_donation_requests_count,
    }
    return render(request, 'blood/admin_dashboard.html', context)

@admin_required(login_url='adminlogin')
def admin_blood_view(request):
    stocks = models.BloodStock.objects.select_related('blood_type').order_by(
        'blood_type__blood_type', 'blood_type__blood_sign'
    )

    if request.method == 'POST':
        stock_ids = request.POST.getlist('stock_id')
        units_list = request.POST.getlist('units_available')

        with transaction.atomic():
            for stock_id, units in zip(stock_ids, units_list):
                try:
                    units_val = int(units)
                    if units_val < 0:
                        messages.error(request, _('Stock cannot be negative.'))
                        return redirect('admin-blood')
                    stock = models.BloodStock.objects.select_for_update().get(pk=stock_id)
                    stock.units_available = units_val
                    stock.save()
                except (ValueError, models.BloodStock.DoesNotExist):
                    messages.error(request, _('Invalid stock data.'))
                    return redirect('admin-blood')

        messages.success(request, _('Blood stock updated successfully.'))
        return redirect('admin-blood')

    context = {
        'stocks': stocks,
    }
    return render(request, 'blood/admin_blood.html', context)


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
                    messages.error(request, _('You cannot deactivate your own account.'))
                else:
                    user.is_active = (action == 'activate')
                    user.save()
                    status_str = _('activated') if user.is_active else _('deactivated')
                    messages.success(request, _('User %(username)s has been %(status)s.') % {'username': user.username, 'status': status_str})
            except User.DoesNotExist:
                messages.error(request, _('User not found.'))
        return redirect('admin-user-management')

    # GET: List all AppUsers with their related auth User
    users = models.AppUser.objects.select_related('user', 'wilaya', 'commune').all()
    return render(request, 'blood/admin_user_management.html', {'users': users})

@admin_required(login_url='adminlogin')
def admin_donor_eligibility_view(request):
    """
    Displays all donors.
    """
    # GET: List all donors via AppUser
    donors = models.AppUser.objects.select_related('user').filter(profil_type='Donor')
    return render(request, 'blood/admin_donor_eligibility.html', {'donors': donors})

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def complete_blood_request_view(request, pk):
    """Approved → Completed. Notifies patient."""
    req = models.BloodRequest.objects.get(id=pk)
    if req.status != 'approved':
        messages.error(request, _('Only approved requests can be marked as completed.'))
        return redirect('admin-dashboard')
    
    with transaction.atomic():
        req.status = 'completed'
        req.save()
        
        models.Notification.objects.create(
            recipient=req.user,
            title=_('Blood Request Completed'),
            message=_('Your blood request status has been updated to Completed.'),
        )
        
    messages.success(request, _('Request has been completed successfully.'))
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
                    recipient=donation_req.user,
                    title=_('Donation Request Cancelled'),
                    message=_("The patient's blood request was cancelled by the admin. Your donation request has been cancelled."),
                )
            
        req.status = 'cancelled_by_admin'
        req.save()
        
        models.Notification.objects.create(
            recipient=req.user,
            title=_('Blood Request Cancelled'),
            message=_('Your blood request status has been updated to Cancelled.'),
        )
        
    messages.success(request, _('Request has been cancelled successfully.'))
    return redirect('admin-dashboard')


@admin_required(login_url='adminlogin')
def admin_blood_requests_view(request):
    form = forms.AdminBloodRequestFilterForm(request.GET or None)
    queryset = models.BloodRequest.objects.select_related(
        'user', 'blood_type', 'wilaya', 'commune'
    ).order_by('-created_at')

    if form.is_valid():
        if form.cleaned_data.get('status'):
            queryset = queryset.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('blood_type'):
            queryset = queryset.filter(blood_type=form.cleaned_data['blood_type'])
        if form.cleaned_data.get('urgency'):
            queryset = queryset.filter(urgency=form.cleaned_data['urgency'])
        if form.cleaned_data.get('wilaya'):
            queryset = queryset.filter(wilaya=form.cleaned_data['wilaya'])
        if form.cleaned_data.get('commune'):
            queryset = queryset.filter(commune=form.cleaned_data['commune'])

    if request.GET.get('status') in (models.STATUS_PENDING, models.STATUS_APPROVED):
        queryset = queryset.prefetch_related('attributions', 'attributions__blood_type')

    context = {
        'filter_form': form,
        'blood_requests': queryset,
        'active_statuses': models.ACTIVE_STATUSES,
        'terminal_statuses': models.TERMINAL_STATUSES,
    }
    return render(request, 'blood/admin_blood_requests.html', context)


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def admin_blood_request_approve_view(request, pk):
    blood_request = models.BloodRequest.objects.select_related('blood_type').get(pk=pk)

    if request.method == 'GET':
        if blood_request.status != models.STATUS_PENDING:
            return JsonResponse({'success': False, 'error': _('Only pending requests can be approved.')}, status=400)
        compatible_ids = services.get_compatible_blood_type_ids(blood_request.blood_type)
        stocks = models.BloodStock.objects.filter(blood_type_id__in=compatible_ids).select_related('blood_type')
        compatible_types = []
        for stock in stocks:
            compatible_types.append({
                'id': stock.blood_type.id,
                'name': str(stock.blood_type),
                'units_available': stock.units_available,
            })
        return JsonResponse({'success': True, 'compatible_types': compatible_types})

    if request.method == 'POST':
        blood_type_ids = request.POST.getlist('blood_type_id')
        units_list = request.POST.getlist('units_attributed')
        if not blood_type_ids or len(blood_type_ids) != len(units_list):
            return JsonResponse({'success': False, 'error': _('Missing or mismatched attribution data.')}, status=400)
        attributions_data = []
        for bt_id, units in zip(blood_type_ids, units_list):
            try:
                attributions_data.append({
                    'blood_type_id': int(bt_id),
                    'units_attributed': int(units),
                })
            except ValueError:
                return JsonResponse({'success': False, 'error': _('Invalid attribution data.')}, status=400)
        try:
            services.approve_blood_request(blood_request, attributions_data)
            models.Notification.objects.create(
                recipient=blood_request.user,
                title=_('Blood Request Approved'),
                message=_('Your blood request has been approved.'),
            )
            messages.success(request, _('Request approved successfully.'))
            return JsonResponse({'success': True})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def admin_blood_request_complete_view(request, pk):
    blood_request = models.BloodRequest.objects.prefetch_related(
        'attributions', 'attributions__blood_type'
    ).get(pk=pk)

    if request.method == 'GET':
        if blood_request.status != models.STATUS_APPROVED:
            return JsonResponse({'success': False, 'error': _('Only approved requests can be completed.')}, status=400)
        attributions = []
        for attr in blood_request.attributions.all():
            attributions.append({
                'blood_type_id': attr.blood_type_id,
                'blood_type_name': str(attr.blood_type),
                'units_attributed': attr.units_attributed,
            })
        return JsonResponse({'success': True, 'attributions': attributions})

    if request.method == 'POST':
        blood_type_ids = request.POST.getlist('blood_type_id')
        units_list = request.POST.getlist('units_attributed')
        if len(blood_type_ids) != len(units_list):
            return JsonResponse({'success': False, 'error': _('Mismatched attribution data.')}, status=400)
        attributions_data = []
        for bt_id, units in zip(blood_type_ids, units_list):
            try:
                attributions_data.append({
                    'blood_type_id': int(bt_id),
                    'units_attributed': int(units),
                })
            except ValueError:
                return JsonResponse({'success': False, 'error': _('Invalid attribution data.')}, status=400)
        try:
            services.complete_blood_request(blood_request, attributions_data)
            from datetime import date
            blood_request.user.last_transfusion_date = date.today()
            blood_request.user.save()
            models.Notification.objects.create(
                recipient=blood_request.user,
                title=_('Blood Request Completed'),
                message=_('Your blood request has been completed.'),
            )
            messages.success(request, _('Request completed successfully.'))
            return JsonResponse({'success': True})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

    return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.BloodRequest, models.TERMINAL_STATUSES)
def admin_blood_request_reject_view(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)

    blood_request = models.BloodRequest.objects.get(pk=pk)
    try:
        services.reject_blood_request(blood_request)
        models.Notification.objects.create(
            recipient=blood_request.user,
            title=_('Blood Request Cancelled'),
            message=_('Your blood request has been cancelled by admin.'),
        )
        messages.success(request, _('Request rejected successfully.'))
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@admin_required(login_url='adminlogin')
def admin_donation_requests_view(request):
    form = forms.AdminDonationRequestFilterForm(request.GET or None)
    queryset = models.DonationRequest.objects.select_related(
        'user', 'user__blood_type', 'wilaya', 'commune'
    ).order_by('-created_at')

    if form.is_valid():
        if form.cleaned_data.get('status'):
            queryset = queryset.filter(status=form.cleaned_data['status'])
        if form.cleaned_data.get('blood_type'):
            queryset = queryset.filter(user__blood_type=form.cleaned_data['blood_type'])
        if form.cleaned_data.get('wilaya'):
            queryset = queryset.filter(wilaya=form.cleaned_data['wilaya'])
        if form.cleaned_data.get('commune'):
            queryset = queryset.filter(commune=form.cleaned_data['commune'])

    context = {
        'filter_form': form,
        'donation_requests': queryset,
        'active_statuses': ['pending', 'approved'],
        'terminal_statuses': models.DONATION_TERMINAL_STATUSES,
    }
    return render(request, 'blood/admin_donation_requests.html', context)


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def approve_donation_view(request, pk):
    """Pending → Approved. Requires selecting an eligible pending BloodRequest. Atomic."""
    req = models.DonationRequest.objects.get(id=pk)
    if req.status != 'pending':
        messages.error(request, _('Only pending requests can be approved.'))
        return redirect('admin-dashboard')
        
    # Get eligible pending blood requests (exact blood type match)
    eligible_blood_requests = models.BloodRequest.objects.filter(
        status='pending',
        blood_type=req.user.blood_type,
    ).select_related('user', 'wilaya', 'commune')
    
    if request.method == 'POST':
        blood_request_id = request.POST.get('blood_request_id')
        if not blood_request_id:
            messages.error(request, _('Please select a blood request.'))
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
                    recipient=req.user,
                    title=_('Donation Request Approved'),
                    message=_('Your donation request status has been updated to Approved.'),
                )
                
                # Notify Patient
                models.Notification.objects.create(
                    recipient=blood_req.user,
                    title=_('Blood Request Approved'),
                    message=_('Your blood request status has been updated to Approved.'),
                )
                
            messages.success(request, _('Request has been approved successfully.'))
            return redirect('admin-dashboard')
            
        except models.BloodRequest.DoesNotExist:
            messages.error(request, _('The selected blood request is no longer available.'))
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
        messages.error(request, _('Only pending requests can be approved.'))
        return redirect('admin-dashboard')
        
    # Get eligible pending donations (exact blood type match)
    eligible_donations = models.DonationRequest.objects.filter(
        status='pending',
        user__blood_type=req.blood_type,
    ).select_related('user', 'wilaya', 'commune')
    
    if request.method == 'POST':
        donation_ids = request.POST.getlist('donation_ids')
        if not donation_ids:
            messages.error(request, _('Please select at least one donor.'))
            return redirect('update-approve-status', pk=pk)
            
        try:
            with transaction.atomic():
                # Lock the donation requests
                selected_donations = models.DonationRequest.objects.select_for_update().filter(
                    id__in=donation_ids, status='pending'
                )
                
                if len(selected_donations) != len(donation_ids):
                    messages.error(request, _('One or more selected donations are no longer available.'))
                    return redirect('update-approve-status', pk=pk)

                # Link and update statuses
                for donation_req in selected_donations:
                    donation_req.blood_request = req
                    donation_req.status = 'approved'
                    donation_req.save()
                    
                    # Notify Donor
                    models.Notification.objects.create(
                        recipient=donation_req.user,
                        title=_('Donation Request Approved'),
                        message=_('Your donation request has been matched and Approved for a Blood Request.'),
                    )

                req.status = 'approved'
                req.save()
                
                # Notify Patient
                models.Notification.objects.create(
                    recipient=req.user,
                    title=_('Blood Request Approved'),
                    message=_('Your blood request status has been updated to Approved and matched with donor(s).'),
                )
                
            messages.success(request, _('Request has been approved successfully.'))
            return redirect('admin-dashboard')
            
        except Exception as e:
            messages.error(request, _('An error occurred while approving the request.'))
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
        messages.error(request, _('Only pending requests can be rejected.'))
        return redirect('admin-dashboard')
        
    req.status = 'rejected'
    req.save()
    
    models.Notification.objects.create(
        recipient=req.user,
        title=_('Donation Request Rejected'),
        message=_('Your donation request status has been updated to Rejected.'),
    )
    messages.success(request, _('Request has been rejected successfully.'))
    return redirect('admin-dashboard')

@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def complete_donation_request_view(request, pk):
    """Approved → Completed. Notifies donor."""
    req = models.DonationRequest.objects.get(id=pk)
    if req.status != 'approved':
        messages.error(request, _('Only approved requests can be marked as completed.'))
        return redirect('admin-dashboard')
        
    with transaction.atomic():
        req.status = 'completed'
        req.save()
        
        # Point 3: Update donor profile
        req.user.last_donation_date = date.today()
        req.user.save()
    
    models.Notification.objects.create(
        recipient=req.user,
        title=_('Donation Completed'),
        message=_('Your donation request status has been updated to Completed.'),
    )
    messages.success(request, _('Request has been completed successfully.'))
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
                recipient=blood_req.user,
                title=_('Donor Request Cancelled'),
                message=_("A donor's request was cancelled by the admin. Your blood request is now pending again."),
            )
            
        req.save()
        
        models.Notification.objects.create(
            recipient=req.user,
            title=_('Donation Request Cancelled'),
            message=_('Your donation request status has been updated to Cancelled by Admin.'),
        )
        
    messages.success(request, _('Request has been cancelled successfully.'))
    return redirect('admin-dashboard')


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def admin_donation_request_approve_view(request, pk):
    """Pending → Approved. Notifies donor."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)

    donation_req = models.DonationRequest.objects.get(pk=pk)
    if donation_req.status != 'pending':
        return JsonResponse({'success': False, 'error': _('Only pending requests can be approved.')}, status=400)

    donation_req.status = 'approved'
    donation_req.save()

    models.Notification.objects.create(
        recipient=donation_req.user,
        title=_('Donation Request Approved'),
        message=_('Your donation request has been approved.'),
    )
    messages.success(request, _('Donation request approved successfully.'))
    return JsonResponse({'success': True})


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def admin_donation_request_complete_view(request, pk):
    """Approved → Completed. Increments BloodStock by 1. Notifies donor."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)

    donation_req = models.DonationRequest.objects.select_related('user__blood_type').get(pk=pk)
    if donation_req.status != 'approved':
        return JsonResponse({'success': False, 'error': _('Only approved requests can be completed.')}, status=400)

    with transaction.atomic():
        # Increment stock for donor's blood type
        stock, created = models.BloodStock.objects.select_for_update().get_or_create(
            blood_type=donation_req.user.blood_type,
            defaults={'units_available': 0}
        )
        stock.units_available += 1
        stock.save()

        # Update donation status
        donation_req.status = 'completed'
        donation_req.save()

        # Update donor last donation date
        donation_req.user.last_donation_date = date.today()
        donation_req.user.save()

    models.Notification.objects.create(
        recipient=donation_req.user,
        title=_('Donation Request Completed'),
        message=_('Your donation request has been completed. Thank you for your donation!'),
    )
    messages.success(request, _('Donation request completed successfully.'))
    return JsonResponse({'success': True})


@admin_required(login_url='adminlogin')
@terminal_status_guard(models.DonationRequest, models.DONATION_TERMINAL_STATUSES)
def admin_donation_request_cancel_view(request, pk):
    """Pending/Approved → Cancelled by Admin. Decrements stock if was approved. Notifies donor."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)

    donation_req = models.DonationRequest.objects.select_related('user__blood_type').get(pk=pk)
    if donation_req.status not in ('pending', 'approved'):
        return JsonResponse({'success': False, 'error': _('Only pending or approved requests can be cancelled.')}, status=400)

    with transaction.atomic():
        # If was approved, decrement stock by 1
        if donation_req.status == 'approved':
            stock = models.BloodStock.objects.select_for_update().filter(
                blood_type=donation_req.user.blood_type
            ).first()
            if stock and stock.units_available > 0:
                stock.units_available -= 1
                stock.save()

        donation_req.status = 'cancelled_by_admin'
        donation_req.save()

    models.Notification.objects.create(
        recipient=donation_req.user,
        title=_('Donation Request Cancelled'),
        message=_('Your donation request has been cancelled by admin.'),
    )
    messages.success(request, _('Donation request cancelled successfully.'))
    return JsonResponse({'success': True})


@admin_required(login_url='adminlogin')
def admin_user_edit_view(request, pk):
    """Get or update user data (email, phone, dob)."""
    app_user = models.AppUser.objects.select_related('user').get(pk=pk)

    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'email': app_user.user.email,
            'phone_number': app_user.phone_number,
            'date_of_birth': app_user.date_of_birth.isoformat(),
        })

    if request.method == 'POST':
        form = forms.AdminUserEditForm(request.POST, user_id=app_user.user.id)
        if form.is_valid():
            # Update email (and username)
            app_user.user.email = form.cleaned_data['email']
            app_user.user.username = form.cleaned_data['email']
            app_user.user.save()

            # Update AppUser fields
            app_user.phone_number = form.cleaned_data['phone_number']
            app_user.date_of_birth = form.cleaned_data['date_of_birth']
            app_user.save()

            messages.success(request, _('User updated successfully.'))
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)


@admin_required(login_url='adminlogin')
def admin_user_delete_view(request, pk):
    """Delete user and all related data."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Invalid request method.')}, status=405)

    app_user = models.AppUser.objects.select_related('user').get(pk=pk)

    # Prevent self-deletion
    if app_user.user == request.user:
        return JsonResponse({'success': False, 'error': _('You cannot delete your own account.')}, status=400)

    # Delete auth.User (cascades to AppUser, BloodRequest, DonationRequest, Notification)
    app_user.user.delete()

    messages.success(request, _('User deleted successfully.'))
    return JsonResponse({'success': True})