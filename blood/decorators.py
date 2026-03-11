from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from blood.models import TERMINAL_STATUSES, DONATION_TERMINAL_STATUSES

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


def terminal_status_guard(model_class, terminal_list, redirect_url='admin-dashboard'):
    """
    Decorator to prevent actions on requests that are in a terminal state.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, pk, *args, **kwargs):
            try:
                obj = model_class.objects.get(pk=pk)
                if obj.status in terminal_list:
                    messages.error(request, f'This request cannot be modified. It is already {obj.status}.')
                    return redirect(redirect_url)
            except model_class.DoesNotExist:
                messages.error(request, 'Request not found.')
                return redirect(redirect_url)
            return view_func(request, pk, *args, **kwargs)
        return _wrapped_view
    return decorator
