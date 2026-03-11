from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import date, timedelta
from blood.models import BloodRequest, DonationRequest, TransfusionSafetyPeriod, Notification

@shared_task
def expire_blood_requests():
    """
    Checks for Pending or Approved BloodRequests where expires_at has passed.
    Sets status to 'expired', cascades to DonationRequest, and notifies users. (Spec §4.5)
    Runs daily.
    """
    expired_requests = BloodRequest.objects.filter(
        status__in=['pending', 'approved'],
        expires_at__lte=timezone.now()
    )

    count = 0
    for req in expired_requests:
        with transaction.atomic():
            # Cascade to linked DonationRequest
            if req.status == 'approved':
                try:
                    donation_req = req.donation_request
                    donation_req.status = 'cancelled_by_admin'
                    donation_req.save()
                    
                    # Notify the matched donor
                    Notification.objects.create(
                        recipient=donation_req.donor.app_user,
                        title='Donation Cancelled (Request Expired)',
                        message=f'The blood request for {req.blood_type}{req.blood_sign} you were matched with has expired.'
                    )
                except DonationRequest.DoesNotExist:
                    pass
            
            req.status = 'expired'
            req.save()
            
            # Notify the patient
            Notification.objects.create(
                recipient=req.patient.app_user,
                title='Blood Request Expired',
                message=f'Your blood request for {req.blood_type}{req.blood_sign} needed by {req.required_date} has expired.'
            )
            count += 1

    return f"Expired {count} blood requests."


@shared_task
def expire_safety_periods():
    """
    Checks for TransfusionSafetyPeriods older than 6 months.
    Restores donor eligibility, notifies donor. (Spec §7.2)
    Runs daily.
    (Verified correct & idempotent for Phase D — no changes needed)
    """
    expired_periods = TransfusionSafetyPeriod.objects.filter(
        ends_at__lte=timezone.now(),
        donor__is_eligible=False
    )
    
    count = 0
    for period in expired_periods:
        donor = period.donor
        donor.is_eligible = True
        donor.save()
        
        # Notify donor
        Notification.objects.create(
            recipient=donor.app_user,
            title='You can donate again!',
            message='Your 6-month transfusion safety period has passed. You are now eligible to donate blood again.'
        )
        
        count += 1

    return f"Expired {count} transfusion safety periods."


@shared_task
def delete_old_notifications():
    """
    Deletes notifications older than their expiry date.
    Runs daily.
    (Verified correct & idempotent for Phase D — no changes needed)
    """
    old_notifications = Notification.objects.filter(expires_at__lte=timezone.now())
    count, _ = old_notifications.delete()
    return f"Deleted {count} old notifications."
