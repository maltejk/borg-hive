from borghive.forms.base import BaseForm
from borghive.models import EmailNotification, PushoverNotification


# pylint: disable=too-few-public-methods
class EmailNotificationForm(BaseForm):
    """
    form for a email notification
    """

    class Meta:
        model = EmailNotification
        fields = (
            "email",
            "group",
        )


# pylint: disable=too-few-public-methods
class PushoverNotificationForm(BaseForm):
    """
    form for a pushover notification
    """

    class Meta:
        model = PushoverNotification
        fields = (
            "name",
            "user",
            "token",
            "group",
        )
