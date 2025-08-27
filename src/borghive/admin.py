from django.contrib import admin
from borghive.models import EmailNotification, PushoverNotification


@admin.register(EmailNotification, PushoverNotification)
class NotifyAdmin(admin.ModelAdmin):
    """
    Admin integration for custom test notify action
    """
    actions = ['test_notify', ]

    @admin.action(
        description="Test Notification"
    )
    def test_notify(self, request, queryset): # pylint: disable=unused-argument
        """send test notification for each notification in queryset"""
        for notification in queryset:
            notification.notify(**notification.get_test_params())



