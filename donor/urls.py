from django.urls import path

from django.contrib.auth.views import LoginView
from . import views
urlpatterns = [
    path('donorlogin', LoginView.as_view(template_name='donor/donorlogin.html'), name='donorlogin'),
    # donorsignup handled by uniform signup in blood app
    path('donor-dashboard', views.donor_dashboard_view, name='donor-dashboard'),
    path('submit-donation', views.submit_donation_request_view, name='submit-donation'),
    path('donation-history', views.donation_history_view, name='donation-history'),
    # make-request and request-history REMOVED — donors do not submit BloodRequests.
    # DonationRequest URLs will be added in Phase C.
]