from django.urls import path

from django.contrib.auth.views import LoginView
from . import views
urlpatterns = [
    path('patientlogin', LoginView.as_view(template_name='patient/patientlogin.html'), name='patientlogin'),
    # patientsignup handled by uniform signup in blood app
    path('patient-dashboard', views.patient_dashboard_view, name='patient-dashboard'),
    path('make-request', views.make_request_view, name='make-request'),
    path('my-request', views.my_request_view, name='my-request'),
    path('cancel-request/<int:pk>', views.cancel_request_view, name='cancel-request'),
    path('notifications', views.notifications_view, name='patient-notifications'),
]