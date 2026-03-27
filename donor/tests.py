from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth.models import User
from blood.models import (
    AppUser, DonorProfile, PatientProfile, BloodRequest, DonationRequest, 
    TransfusionSafetyPeriod, Wilaya, Commune, Notification
)

class DonorViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.w1 = Wilaya.objects.create(code='01', name='W1')
        self.c1 = Commune.objects.create(wilaya=self.w1, name='C1')        
        
        # Create a male donor
        self.user_m = User.objects.create_user(username='donor_m@a.com', password='pw')
        self.app_user_m = AppUser.objects.create(
            user=self.user_m, first_name='Donor', last_name='Male', gender='M',
            date_of_birth=date(1994, 1, 1), phone_number='111', nin='111111111111111111', blood_type='A', blood_sign='+',
            wilaya=self.w1, commune=self.c1
        )
        self.donor_m = DonorProfile.objects.create(app_user=self.app_user_m)
        
        # Create a female donor
        self.user_f = User.objects.create_user(username='donor_f@a.com', password='pw')
        self.app_user_f = AppUser.objects.create(
            user=self.user_f, first_name='Donor', last_name='Female', gender='F',
            date_of_birth=date(1999, 1, 1), phone_number='222', nin='222222222222222222', blood_type='O', blood_sign='-',
            wilaya=self.w1, commune=self.c1
        )
        self.donor_f = DonorProfile.objects.create(app_user=self.app_user_f)
        
        # Default login with male donor
        self.client.login(username='donor_m@a.com', password='pw')

    def test_donor_dashboard_loads(self):
        response = self.client.get(reverse('donor-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Donor Male')
        self.assertContains(response, 'A')

    def test_submit_donation_request_success(self):
        data = {
            'donated_last_3_months': False,
            'transfusion_last_6_months': False,
            'surgery_last_6_months': False,
            'has_fever': False,
            'on_medication': False,
            'has_anemia': False,
            'confirmed_accurate': True,
            'confirmed_understands': True,
        }
        response = self.client.post(reverse('submit-donation'), data)
        self.assertRedirects(response, reverse('donor-dashboard'))
        
        dr = DonationRequest.objects.filter(donor=self.donor_m).first()
        self.assertIsNotNone(dr)
        self.assertEqual(dr.status, 'pending')

    def test_submit_donation_request_female_fields(self):
        # Male should not have these fields rendered
        response_m = self.client.get(reverse('submit-donation'))
        self.assertNotContains(response_m, 'name="is_pregnant"')
        self.assertNotContains(response_m, 'name="is_breastfeeding"')
        
        # Female should
        self.client.logout()
        self.client.login(username='donor_f@a.com', password='pw')
        response_f = self.client.get(reverse('submit-donation'))
        self.assertContains(response_f, 'name="is_pregnant"')
        self.assertContains(response_f, 'name="is_breastfeeding"')

    def test_submit_blocks_when_active_request_exists(self):
        DonationRequest.objects.create(donor=self.donor_m, status='pending')
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))
        
        # Post should also block
        response = self.client.post(reverse('submit-donation'), {})
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_active_blood_request(self):
        patient = PatientProfile.objects.create(app_user=self.app_user_m)
        BloodRequest.objects.create(
            patient=patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='pending'
        )
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_safety_period_active(self):
        br = BloodRequest.objects.create(
            patient=PatientProfile.objects.create(app_user=self.app_user_m), 
            blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='completed'
        )
        TransfusionSafetyPeriod.objects.create(
            donor=self.donor_m,
            blood_request=br,
            started_at=timezone.now()
        )
        self.donor_m.is_eligible = False
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_ineligible(self):
        self.donor_m.is_eligible = False
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_chronic_disease(self):
        self.donor_m.chronic_disease = True
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_anemia(self):
        self.donor_m.anemia = True
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_blocks_when_recent_donation(self):
        # Donated 2 months ago (less than 3 months)
        self.donor_m.last_donation_date = timezone.now().date() - timedelta(days=60)
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_allowed_when_donation_is_old(self):
        # Donated 4 months ago (more than 3 months)
        self.donor_m.last_donation_date = timezone.now().date() - timedelta(days=120)
        self.donor_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertEqual(response.status_code, 200)

    def test_submit_blocks_when_under_18(self):
        # Update user date of birth to be 17 years ago
        self.app_user_m.date_of_birth = date.today() - timedelta(days=17*365.25)
        self.app_user_m.save()
        
        response = self.client.get(reverse('submit-donation'))
        self.assertRedirects(response, reverse('donor-dashboard'))

    def test_submit_fails_when_transfusion_checked(self):
        data = {
            'donated_last_3_months': False,
            'transfusion_last_6_months': True,
            'surgery_last_6_months': False,
            'has_fever': False,
            'on_medication': False,
            'has_anemia': False,
            'confirmed_accurate': True,
            'confirmed_understands': True,
        }
        response = self.client.post(reverse('submit-donation'), data)
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertContains(response, 'Your donation request cannot be submitted because you received a transfusion', status_code=200, html=False)
        self.assertFalse(DonationRequest.objects.filter(donor=self.donor_m).exists())

    def test_submit_fails_when_surgery_checked(self):
        data = {
            'donated_last_3_months': False,
            'transfusion_last_6_months': False,
            'surgery_last_6_months': True,
            'has_fever': False,
            'on_medication': False,
            'has_anemia': False,
            'confirmed_accurate': True,
            'confirmed_understands': True,
        }
        response = self.client.post(reverse('submit-donation'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your donation request cannot be submitted because you had surgery in the last 6 months.', html=False)

    def test_submit_fails_when_anemia_checked(self):
        data = {
            'donated_last_3_months': False,
            'transfusion_last_6_months': False,
            'surgery_last_6_months': False,
            'has_fever': False,
            'on_medication': False,
            'has_anemia': True,
            'confirmed_accurate': True,
            'confirmed_understands': True,
        }
        response = self.client.post(reverse('submit-donation'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your donation request cannot be submitted because you have anemia.', html=False)

    def test_submit_fails_when_female_pregnant(self):
        self.client.logout()
        self.client.login(username='donor_f@a.com', password='pw')
        data = {
            'donated_last_3_months': False,
            'transfusion_last_6_months': False,
            'surgery_last_6_months': False,
            'has_fever': False,
            'on_medication': False,
            'has_anemia': False,
            'is_pregnant': True,
            'is_breastfeeding': False,
            'confirmed_accurate': True,
            'confirmed_understands': True,
        }
        response = self.client.post(reverse('submit-donation'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your donation request cannot be submitted because you are pregnant or breastfeeding.', html=False)

    def test_cancel_donation_pending(self):
        dr = DonationRequest.objects.create(donor=self.donor_m, status='pending')
        
        response = self.client.post(reverse('cancel-donation', args=[dr.id]))
        self.assertRedirects(response, reverse('donor-dashboard'))
        
        dr.refresh_from_db()
        self.assertEqual(dr.status, 'cancelled_by_user')

    def test_dashboard_eligibility_logic(self):
        # 1. Under 18
        self.app_user_m.date_of_birth = date.today() - timedelta(days=17*365)
        self.app_user_m.save()
        response = self.client.get(reverse('donor-dashboard'))
        self.assertContains(response, 'You are under 18 years old.')
        
        # 2. Chronic Disease (reset age first)
        self.app_user_m.date_of_birth = date(1990,1,1)
        self.app_user_m.save()
        self.donor_m.chronic_disease = True
        self.donor_m.save()
        response = self.client.get(reverse('donor-dashboard'))
        self.assertContains(response, 'You have a chronic disease.')
        
        # 3. Recent Donation (90 days)
        self.donor_m.chronic_disease = False
        self.donor_m.last_donation_date = date.today() - timedelta(days=10)
        self.donor_m.save()
        response = self.client.get(reverse('donor-dashboard'))
        self.assertContains(response, 'Last donation was 10 days ago.')
        self.assertContains(response, 'Next Eligibility') # Badge check

    def test_cancel_donation_approved_cascades(self):
        patient = PatientProfile.objects.create(app_user=self.app_user_f)
        br = BloodRequest.objects.create(
            patient=patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='approved'
        )
        dr = DonationRequest.objects.create(donor=self.donor_m, blood_request=br, status='approved')
        
        # Execute cancel
        response = self.client.post(reverse('cancel-donation', args=[dr.id]))
        self.assertRedirects(response, reverse('donor-dashboard'))
        
        # Verify Cascade
        dr.refresh_from_db()
        br.refresh_from_db()
        self.assertEqual(dr.status, 'cancelled_by_user')
        self.assertIsNone(dr.blood_request)
        self.assertEqual(br.status, 'pending')
        
        # Verify Notification
        notif = Notification.objects.filter(recipient=patient.app_user).first()
        self.assertIsNotNone(notif)
        self.assertIn('cancelled', notif.message)

    def test_cancel_terminal_donation_fails(self):
        dr = DonationRequest.objects.create(donor=self.donor_m, status='completed')
        
        response = self.client.post(reverse('cancel-donation', args=[dr.id]))
        
        dr.refresh_from_db()
        self.assertEqual(dr.status, 'completed')

    def test_donation_history_loads(self):
        url = reverse('donation-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'donor/donation_history.html')

    def test_donor_notifications_loads(self):
        url = reverse('donor-notifications')
        # Create a notification
        Notification.objects.create(
            recipient=self.app_user_m, # Changed from self.app_user to self.app_user_m to match existing setup
            title="Test notification",
            message="Test message"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'donor/notifications.html')
        # Verify it marks as read
        self.assertFalse(Notification.objects.filter(recipient=self.app_user_m, is_read=False).exists()) # Changed from self.app_user to self.app_user_m
