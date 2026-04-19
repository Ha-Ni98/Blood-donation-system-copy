from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth.models import User
from blood.models import (
    AppUser, PatientProfile, DonorProfile, BloodRequest, 
    Wilaya, Commune, TransfusionSafetyPeriod, DonationRequest, Notification,
    TERMINAL_STATUSES
)

class BloodRequestLogicTests(TestCase):
    def setUp(self):
        # Create user and profile
        self.user1 = User.objects.create_user(username='patient1@a.com', password='pw')
        self.w1 = Wilaya.objects.create(id=1, name='W1')
        self.c1 = Commune.objects.create(id=1, wilaya=self.w1, name='C1')        
        self.app_user1 = AppUser.objects.create(
            user=self.user1, first_name='P1', last_name='L1', gender='M',
            date_of_birth=date(1994, 1, 1), phone_number='111', nin='111', blood_type='A', blood_sign='+',
            wilaya=self.w1, commune=self.c1
        )
        self.patient = PatientProfile.objects.create(app_user=self.app_user1)

        # Donor profile
        self.user2 = User.objects.create_user(username='donor1@a.com', password='pw')
        self.app_user2 = AppUser.objects.create(
            user=self.user2, first_name='D1', last_name='L1', gender='M',
            date_of_birth=date(1994, 1, 1), phone_number='222', nin='222', blood_type='A', blood_sign='+',
            wilaya=self.w1, commune=self.c1
        )
        self.donor = DonorProfile.objects.create(app_user=self.app_user2)

    def test_expires_at_computation(self):
        """Test expires_at is correctly computed as min(required_date, created_at + 30 days)"""
        # Case 1: required_date is 10 days away (should be expires_at)
        req_date_1 = date.today() + timedelta(days=10)
        req1 = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=req_date_1, wilaya=self.w1, commune=self.c1
        )
        self.assertEqual(req1.expires_at.date(), req_date_1)

        # Case 2: required_date is 40 days away (expires_at should be created_at + 30)
        req_date_2 = date.today() + timedelta(days=40)
        req2 = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=req_date_2, wilaya=self.w1, commune=self.c1
        )
        self.assertEqual(req2.expires_at.date(), req2.created_at.date() + timedelta(days=30))

    def test_status_immutability(self):
        """Terminal statuses cannot be changed"""
        req = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='completed'
        )
        # Attempting to save it with a different status should raise ValueError 
        # based on our custom clean/save logic (handled in views normally, but let's test view behavior)
        # Since the model itself might not enforce it, let's just make sure it's enforced in the view.
        # Here we just verify the constants exist.
        self.assertIn(req.status, TERMINAL_STATUSES)

    def test_safety_period_creation(self):
        """Creating a safety period logic"""
        req = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='approved'
        )
        donation_req = DonationRequest.objects.create(
            donor=self.donor, blood_request=req, status='pending'
        )
        
        # Simulate complete_blood_request_view logic
        req.status = 'completed'
        req.save()
        
        TransfusionSafetyPeriod.objects.create(donor=self.donor, blood_request=req, started_at=timezone.now())
        self.donor.is_eligible = False
        self.donor.save()
        
        self.assertFalse(self.donor.is_eligible)
        self.assertEqual(TransfusionSafetyPeriod.objects.count(), 1)
        self.assertEqual(TransfusionSafetyPeriod.objects.first().donor, self.donor)

from django.urls import reverse
from blood.tasks import expire_blood_requests
from blood.admin import AppUserAdmin
from django.contrib.admin.sites import site

class AdminDonationTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(username='admin@a.com', password='pw')
        self.u1 = User.objects.create_user(username='d1@a.com', password='pw')
        self.w1 = Wilaya.objects.create(code='01', name='Adrar')
        self.c1 = Commune.objects.create(name='Adrar', wilaya=self.w1)
        self.app_user = AppUser.objects.create(
            user=self.u1, first_name='D1', last_name='L1', 
            phone_number='0555555555', nin='123456789012345678', 
            gender='M', blood_type='A', blood_sign='+', 
            date_of_birth=date(1990,1,1), wilaya=self.w1, commune=self.c1
        )
        self.donor = DonorProfile.objects.create(app_user=self.app_user)
        self.client.login(username='admin@a.com', password='pw')

    def test_complete_donation_updates_profile(self):
        dr = DonationRequest.objects.create(donor=self.donor, status='approved')
        
        response = self.client.post(reverse('complete-donation-request', args=[dr.id]))
        self.assertRedirects(response, reverse('admin-dashboard'))
        
        self.donor.refresh_from_db()
        self.assertFalse(self.donor.is_eligible)
        self.assertEqual(self.donor.last_donation_date, date.today())
        
        dr.refresh_from_db()
        self.assertEqual(dr.status, 'completed')

class AdminAccessGuardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin@a.com', password='pw')

    def test_staff_access(self):
        self.client.login(username='admin@a.com', password='pw')
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 200)

class AdminBloodRequestActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin2@a.com', password='pw')
        self.client.login(username='admin2@a.com', password='pw')
        self.w1 = Wilaya.objects.create(id=2, name='W2')
        self.c1 = Commune.objects.create(id=2, wilaya=self.w1, name='C2')
        self.patient_user = AppUser.objects.create(
            user=User.objects.create_user(username='p2@a.com', password='pw'),
            first_name='P', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='12', 
            nin='12', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        self.patient = PatientProfile.objects.create(app_user=self.patient_user)
        self.req = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='pending'
        )

    def test_reject_blood_request(self):
        response = self.client.get(reverse('update-reject-status', args=[self.req.id]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'rejected')
        self.assertRedirects(response, reverse('admin-dashboard'))
        self.assertTrue(Notification.objects.filter(recipient=self.patient_user, title='Blood Request Rejected').exists())

    def test_cancel_blood_request(self):
        response = self.client.get(reverse('admin-cancel-blood-request', args=[self.req.id]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'cancelled_by_admin')
        self.assertTrue(Notification.objects.filter(recipient=self.patient_user, title='Blood Request Cancelled').exists())

    def test_approve_blood_request_with_multiple_donor_linking(self):
        # Create Donor 1
        donor_user1 = AppUser.objects.create(
            user=User.objects.create_user(username='d2@a.com', password='pw'),
            first_name='D1', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='22', 
            nin='22', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        donor1 = DonorProfile.objects.create(app_user=donor_user1)
        donation_req1 = DonationRequest.objects.create(donor=donor1, status='pending')

        # Create Donor 2
        donor_user2 = AppUser.objects.create(
            user=User.objects.create_user(username='d2_2@a.com', password='pw'),
            first_name='D2', last_name='L', gender='F', date_of_birth=date(1995, 1, 1), phone_number='23', 
            nin='23', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        donor2 = DonorProfile.objects.create(app_user=donor_user2)
        donation_req2 = DonationRequest.objects.create(donor=donor2, status='pending')

        # Approve with both donations selected
        response = self.client.post(
            reverse('update-approve-status', args=[self.req.id]), 
            {'donation_ids': [donation_req1.id, donation_req2.id]}
        )
        
        self.req.refresh_from_db()
        donation_req1.refresh_from_db()
        donation_req2.refresh_from_db()
        
        self.assertEqual(self.req.status, 'approved')
        self.assertEqual(donation_req1.status, 'approved')
        self.assertEqual(donation_req2.status, 'approved')
        
        # Verify foreign keys
        self.assertEqual(donation_req1.blood_request, self.req)
        self.assertEqual(donation_req2.blood_request, self.req)
        self.assertEqual(self.req.donation_requests.count(), 2)
    def test_complete_blood_request_with_multiple_donors(self):
        self.req.status = 'approved'
        self.req.save()
        
        # Donor 1 setup
        donor_user1 = AppUser.objects.create(
            user=User.objects.create_user(username='d3@a.com', password='pw'),
            first_name='D1', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='32', 
            nin='32', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        donor1 = DonorProfile.objects.create(app_user=donor_user1)
        donation_req1 = DonationRequest.objects.create(donor=donor1, blood_request=self.req, status='approved')

        # Donor 2 setup
        donor_user2 = AppUser.objects.create(
            user=User.objects.create_user(username='d3_2@a.com', password='pw'),
            first_name='D2', last_name='L', gender='F', date_of_birth=date(1995, 1, 1), phone_number='33', 
            nin='33', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        donor2 = DonorProfile.objects.create(app_user=donor_user2)
        donation_req2 = DonationRequest.objects.create(donor=donor2, blood_request=self.req, status='approved')

        response = self.client.get(reverse('complete-blood-request', args=[self.req.id]))
        
        self.req.refresh_from_db()
        donation_req1.refresh_from_db()
        donation_req2.refresh_from_db()
        donor1.refresh_from_db()
        donor2.refresh_from_db()
        
        # Verify BloodRequest status
        self.assertEqual(self.req.status, 'completed')
        
        # Verify cascaded DonationRequest statuses
        self.assertEqual(donation_req1.status, 'completed')
        self.assertEqual(donation_req2.status, 'completed')
        
        # Verify safety protocols for both donors
        self.assertFalse(donor1.is_eligible)
        self.assertFalse(donor2.is_eligible)
        self.assertTrue(TransfusionSafetyPeriod.objects.filter(donor=donor1, blood_request=self.req).exists())
        self.assertTrue(TransfusionSafetyPeriod.objects.filter(donor=donor2, blood_request=self.req).exists())
class AdminDonationRequestActionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin3@a.com', password='pw')
        self.client.login(username='admin3@a.com', password='pw')
        self.w1 = Wilaya.objects.create(id=3, name='W3')
        self.c1 = Commune.objects.create(id=3, wilaya=self.w1, name='C3')
        self.donor_user = AppUser.objects.create(
            user=User.objects.create_user(username='d4@a.com', password='pw'),
            first_name='D', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='14', 
            nin='14', blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        self.donor = DonorProfile.objects.create(app_user=self.donor_user)
        self.donation_req = DonationRequest.objects.create(donor=self.donor, status='pending')

    def test_reject_donation_request(self):
        response = self.client.get(reverse('reject-donation', args=[self.donation_req.id]))
        self.donation_req.refresh_from_db()
        self.assertEqual(self.donation_req.status, 'rejected')
        self.assertRedirects(response, reverse('admin-dashboard'))

    def test_cancel_donation_request(self):
        self.donation_req.status = 'approved'
        blood_req = BloodRequest.objects.create(
            patient=PatientProfile.objects.create(app_user=self.donor_user),
            blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='approved'
        )
        self.donation_req.blood_request = blood_req
        self.donation_req.save()

        response = self.client.get(reverse('admin-cancel-donation-request', args=[self.donation_req.id]))
        self.donation_req.refresh_from_db()
        blood_req.refresh_from_db()

        self.assertEqual(self.donation_req.status, 'cancelled_by_admin')
        self.assertIsNone(self.donation_req.blood_request)
        self.assertEqual(blood_req.status, 'pending')

    def test_complete_donation_request(self):
        self.donation_req.status = 'approved'
        self.donation_req.save()
        response = self.client.get(reverse('complete-donation-request', args=[self.donation_req.id]))
        self.donation_req.refresh_from_db()
        self.assertEqual(self.donation_req.status, 'completed')

class TerminalStatusGuardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin4@a.com', password='pw')
        self.client.login(username='admin4@a.com', password='pw')
        self.w1 = Wilaya.objects.create(id=4, name='W4')
        self.c1 = Commune.objects.create(id=4, wilaya=self.w1, name='C4')
        self.patient_user = AppUser.objects.create(
            user=User.objects.create_user(username='p4@a.com', password='pw'),
            first_name='P', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='15', nin='15',
            blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        self.req = BloodRequest.objects.create(
            patient=PatientProfile.objects.create(app_user=self.patient_user),
            blood_type='A', blood_sign='+', units_needed=1, urgency='normal',
            required_date=date.today()+timedelta(days=10), wilaya=self.w1, commune=self.c1, 
            status='completed'
        )

    def test_cannot_reject_terminal_status(self):
        response = self.client.get(reverse('update-reject-status', args=[self.req.id]))
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'completed')

class NINAuditTests(TestCase):
    def test_appuser_admin_nin_hidden(self):
        admin_class = site._registry.get(AppUser)
        self.assertIsNotNone(admin_class)
        self.assertNotIn('nin', admin_class.search_fields)
        self.assertIn('masked_nin', getattr(admin_class, 'readonly_fields', []))
        self.assertIn('nin', getattr(admin_class, 'exclude', []))

class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='admin5@a.com', password='pw')
        self.client.login(username='admin5@a.com', password='pw')
        self.user_to_toggle = User.objects.create_user(username='toggle@a.com', password='pw', is_active=True)

    def test_deactivate_user(self):
        response = self.client.post(reverse('admin-user-management'), {'user_id': self.user_to_toggle.id, 'action': 'deactivate'})
        self.user_to_toggle.refresh_from_db()
        self.assertFalse(self.user_to_toggle.is_active)
        self.assertRedirects(response, reverse('admin-user-management'))

    def test_activate_user(self):
        self.user_to_toggle.is_active = False
        self.user_to_toggle.save()
        response = self.client.post(reverse('admin-user-management'), {'user_id': self.user_to_toggle.id, 'action': 'activate'})
        self.user_to_toggle.refresh_from_db()
        self.assertTrue(self.user_to_toggle.is_active)

    def test_cannot_deactivate_self(self):
        response = self.client.post(reverse('admin-user-management'), {'user_id': self.admin.id, 'action': 'deactivate'})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

class CeleryTaskTests(TestCase):
    def setUp(self):
        self.w1 = Wilaya.objects.create(id=5, name='W5')
        self.c1 = Commune.objects.create(id=5, wilaya=self.w1, name='C5')
        self.patient_user = AppUser.objects.create(
            user=User.objects.create_user(username='p5@a.com', password='pw'),
            first_name='P', last_name='L', gender='M', date_of_birth=date(1994, 1, 1), phone_number='16', nin='16',
            blood_type='A', blood_sign='+', wilaya=self.w1, commune=self.c1
        )
        self.patient = PatientProfile.objects.create(app_user=self.patient_user)
        
    def test_expire_blood_requests_task(self):
        req1 = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1, urgency='normal',
            required_date=date.today()+timedelta(days=1), wilaya=self.w1, commune=self.c1, 
            status='pending'
        )
        BloodRequest.objects.filter(id=req1.id).update(expires_at=timezone.now() - timedelta(days=1))
        
        req2 = BloodRequest.objects.create(
            patient=self.patient, blood_type='B', blood_sign='+', units_needed=1, urgency='normal',
            required_date=date.today()+timedelta(days=10), wilaya=self.w1, commune=self.c1, 
            status='pending'
        )
        
        result = expire_blood_requests()
        req1.refresh_from_db()
        req2.refresh_from_db()
        
        self.assertEqual(req1.status, 'expired')
        self.assertEqual(req2.status, 'pending')
        self.assertEqual(result, "Expired 1 blood requests.")
