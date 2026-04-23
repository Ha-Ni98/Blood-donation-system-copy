"""bloodbankmanagement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""
bloodbankmanagement URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView, LoginView
from blood import views
from django.conf.urls.i18n import i18n_patterns



urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    # API endpoints that don't need i18n prefix
    path('api/communes/', views.communes_api, name='api-communes'),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    path('donor/', include('donor.urls')),
    path('patient/', include('patient.urls')),

    path('', views.home_view, name='home'),
    path('login', views.login_view, name='login'),
    path('signup', views.signup_view, name='signup'),
    path('patient/add-donor-profile', views.create_donor_profile_from_patient_view, name='create-donor-profile-from-patient'),
    path('donor/add-patient-profile', views.create_patient_profile_from_donor_view, name='create-patient-profile-from-donor'),
    path('logout', LogoutView.as_view(template_name='blood/logout.html'), name='logout'),

    path('afterlogin', views.afterlogin_view, name='afterlogin'),
    path('adminlogin', LoginView.as_view(template_name='blood/adminlogin.html'), name='adminlogin'),
    path('admin-dashboard', views.admin_dashboard_view, name='admin-dashboard'),
    path('admin-blood', views.admin_blood_view, name='admin-blood'),
    path('admin-blood-requests', views.admin_blood_requests_view, name='admin-blood-requests'),
    path('admin-blood-request/<int:pk>/approve', views.admin_blood_request_approve_view, name='admin-blood-request-approve'),
    path('admin-blood-request/<int:pk>/complete', views.admin_blood_request_complete_view, name='admin-blood-request-complete'),
    path('admin-blood-request/<int:pk>/reject', views.admin_blood_request_reject_view, name='admin-blood-request-reject'),
    path('admin-user-management', views.admin_user_management_view, name='admin-user-management'),
    path('admin-donor-eligibility', views.admin_donor_eligibility_view, name='admin-donor-eligibility'),
    path('admin-donation-requests', views.admin_donation_requests_view, name='admin-donation-requests'),
    path('admin-donation-request/<int:pk>/approve', views.admin_donation_request_approve_view, name='admin-donation-request-approve'),
    path('admin-donation-request/<int:pk>/complete', views.admin_donation_request_complete_view, name='admin-donation-request-complete'),
    path('admin-donation-request/<int:pk>/cancel', views.admin_donation_request_cancel_view, name='admin-donation-request-cancel'),
    path('admin-user/<int:pk>/edit', views.admin_user_edit_view, name='admin-user-edit'),
    path('admin-user/<int:pk>/delete', views.admin_user_delete_view, name='admin-user-delete'),
)