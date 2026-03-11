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
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    path('donor/', include('donor.urls')),
    path('patient/', include('patient.urls')),

    path('', views.home_view, name='home'),
    path('login', views.login_view, name='login'),
    path('signup', views.signup_view, name='signup'),
    path('choose-profile', views.choose_profile_view, name='choose-profile'),
    path('patient/create-profile', views.create_patient_profile_view, name='create-patient-profile'),
    path('donor/create-profile', views.create_donor_profile_view, name='create-donor-profile'),
    path('patient/add-donor-profile', views.create_donor_profile_from_patient_view, name='create-donor-profile-from-patient'),
    path('donor/add-patient-profile', views.create_patient_profile_from_donor_view, name='create-patient-profile-from-donor'),
    path('api/communes/', views.communes_api, name='api-communes'),
    path('logout', LogoutView.as_view(template_name='blood/logout.html'), name='logout'),

    path('afterlogin', views.afterlogin_view, name='afterlogin'),
    path('adminlogin', LoginView.as_view(template_name='blood/adminlogin.html'), name='adminlogin'),
    path('admin-dashboard', views.admin_dashboard_view, name='admin-dashboard'),
    path('admin-blood', views.admin_blood_view, name='admin-blood'),
    path('admin-user-management', views.admin_user_management_view, name='admin-user-management'),
    path('update-approve-status/<int:pk>', views.update_approve_status_view, name='update-approve-status'),
    path('update-reject-status/<int:pk>', views.update_reject_status_view, name='update-reject-status'),
    path('complete-blood-request/<int:pk>', views.complete_blood_request_view, name='complete-blood-request'),
    path('admin-cancel-blood-request/<int:pk>', views.admin_cancel_blood_request_view, name='admin-cancel-blood-request'),
)