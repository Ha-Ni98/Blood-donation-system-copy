"""
blood/context_processors.py
Injects unread_notification_count into every template rendered with a RequestContext.
Only fires for authenticated users who have an AppUser (patient or donor).
"""
from blood.models import Notification, AppUser


def unread_notifications(request):
    count = 0
    if request.user.is_authenticated:
        try:
            app_user = request.user.app_user
            count = Notification.objects.filter(recipient=app_user, is_read=False).count()
        except AppUser.DoesNotExist:
            pass
    return {'unread_notification_count': count}
