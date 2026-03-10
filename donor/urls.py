from django.urls import path

from django.contrib.auth.views import LoginView
from . import views
urlpatterns = [
    path('donorlogin', LoginView.as_view(template_name='donor/donorlogin.html'), name='donorlogin'),
    # donorsignup handled by uniform signup in blood app
    path('donor-dashboard', views.donor_dashboard_view, name='donor-dashboard'),
    path('donate-blood', views.donate_blood_view, name='donate-blood'),
    path('donation-history', views.donation_history_view, name='donation-history'),
    # make-request and request-history REMOVED — donors do not submit BloodRequests.
    # DonationRequest URLs will be added in Phase C.
]