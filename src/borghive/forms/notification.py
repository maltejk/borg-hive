from borghive.forms.base import BaseForm
from borghive.models import EmailNotification, PushoverNotification, PagerDutyNotification


class EmailNotificationForm(BaseForm):
    """
    form for a email notification
    """

    class Meta:
        model = EmailNotification
        fields = ('email', 'group',)


class PushoverNotificationForm(BaseForm):
    """
    form for a pushover notification
    """

    class Meta:
        model = PushoverNotification
        fields = ('name', 'user', 'token', 'group',)


class PagerDutyNotificationForm(BaseForm):
    """
    form for a PagerDuty notification
    """

    class Meta:
        model = PagerDutyNotification
        fields = ('name', 'integration_key', 'group',)
