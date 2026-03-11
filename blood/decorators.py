from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def is_admin(user):
    return user.is_authenticated and user.is_staff

def admin_required(function=None, redirect_field_name='next', login_url='adminlogin'):
    """
    Decorator for views that checks that the user is logged in and is a staff member.
    Redirects to adminlogin if they are not logged in/staff.
    """
    actual_decorator = user_passes_test(
        is_admin,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
