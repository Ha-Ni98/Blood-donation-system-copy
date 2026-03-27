from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth.models import User
from blood.models import (
    AppUser, PatientProfile, BloodRequest, Wilaya, Commune
)

class PatientViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='patient1@a.com', password='pw')
        self.w1 = Wilaya.objects.create(id=1, name='W1')
        self.c1 = Commune.objects.create(id=1, wilaya=self.w1, name='C1')        
        self.app_user = AppUser.objects.create(
            user=self.user, first_name='P1', last_name='L1', gender='M',
            date_of_birth=date(1994, 1, 1), phone_number='111', nin='111', blood_type='A', blood_sign='+',
            wilaya=self.w1, commune=self.c1
        )
        self.patient = PatientProfile.objects.create(app_user=self.app_user)
        self.client.login(username='patient1@a.com', password='pw')

    def test_patient_dashboard_loads(self):
        response = self.client.get(reverse('patient-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P1 L1')
        self.assertContains(response, 'A+')

    def test_make_request_view_blocks_duplicate(self):
        # Create an active request first
        BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='pending'
        )
        
        # Accessing make-request should not fail but should redirect or show a warning
        response = self.client.get(reverse('make-request'))
        # Our implementation redirects to patient-dashboard with a toast if there's an active request
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('patient-dashboard'))

    def test_cancel_request_view(self):
        # Create a pending request
        req = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='pending'
        )

        response = self.client.post(reverse('cancel-request', args=[req.id]))
        # Should redirect to my_request_view
        self.assertRedirects(response, reverse('my-request'))
        
        # Reload object from db
        req.refresh_from_db()
        self.assertEqual(req.status, 'cancelled_by_user')

    def test_cancel_terminal_request_fails(self):
        # Create a completed request
        req = BloodRequest.objects.create(
            patient=self.patient, blood_type='A', blood_sign='+', units_needed=1,
            urgency='normal', required_date=date.today()+timedelta(days=10),
            wilaya=self.w1, commune=self.c1, status='completed'
        )

        response = self.client.post(reverse('cancel-request', args=[req.id]))
        # Should still redirect but NOT change the state
        req.refresh_from_db()
        self.assertEqual(req.status, 'completed')
