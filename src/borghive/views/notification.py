import logging
from smtplib import SMTPException
import requests.exceptions

from django.contrib import messages
from django.shortcuts import redirect, reverse, render
from django.urls import reverse_lazy
from django.views.generic import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView

import borghive.forms
from borghive.forms import (
    AlertPreferenceForm,
    EmailNotificationForm,
    PushoverNotificationForm,
)
from borghive.views.base import BaseView
from borghive.models import EmailNotification, PushoverNotification, Notification

# pylint: disable=protected-access,arguments-differ,no-member,too-many-ancestors


LOGGER = logging.getLogger(__name__)


class NotificationBaseView(BaseView):
    """
    Notification Base View for form views
    """

    request = None  # populated by View class

    def form_valid(self, form):
        """form valid function"""
        form.instance.owner = self.request.user
        messages.add_message(self.request, messages.SUCCESS, f"Added: {form.instance}")
        return super().form_valid(form)

    def form_invalid(self, form):
        """form invalid function"""
        for field in form._errors:
            message = ""
            for msg in form._errors[field]:
                message += "<p>" + msg + "</p>"
            messages.add_message(self.request, messages.ERROR, message)
        return redirect(reverse("notification-list"))


class NotificationListView(BaseView, ListView):
    """
    notification list and alert preference
    """

    template_name = "borghive/notification_list.html"
    queryset = Notification.objects.all()

    def get_context_data(self, *args, **kwargs):
        """get context for notification list"""
        context = super().get_context_data(*args, **kwargs)
        alert_preference = self.request.user.alertpreference
        context["alert_preference_form"] = AlertPreferenceForm(
            instance=alert_preference
        )
        return context

    def post(self, request):
        """handle alert preference update"""

        if "alert-pref" in self.request.POST:
            obj = request.user.alertpreference
            alert_preference = AlertPreferenceForm(data=request.POST, instance=obj)
            if alert_preference.is_valid():
                alert_preference.save()
                messages.add_message(
                    self.request, messages.SUCCESS, "Alert preference saved"
                )
            else:
                messages.add_message(
                    self.request, messages.ERROR, "Alert preference save failed"
                )

        return redirect(reverse("notification-list"))


class NotificationDetailView(BaseView, DetailView):
    """ssh public key detail"""

    model = Notification


class NotificationDeleteView(BaseView, DeleteView):
    """notification delete"""

    model = Notification
    success_url = reverse_lazy("notification-list")
    template_name = "borghive/notification_delete.html"

    def get_form_kwargs(self):
        """Remove owner and user kwargs that BaseForm or Form doesn't accept"""
        kwargs = super().get_form_kwargs()
        kwargs.pop("owner", None)
        kwargs.pop("user", None)
        return kwargs


class NotificationCreateView(NotificationBaseView, CreateView):
    """notification create view - handle parse errors"""

    template_name = "borghive/notification_create.html"
    success_url = reverse_lazy("notification-list")
    n_type = None

    def dispatch(self, *args, **kwargs):
        """get notification type and init form of this type"""
        self.n_type = kwargs.pop("n_type", "None")

        if self.n_type == "email":
            LOGGER.debug("get email form")
            self.model = EmailNotification
            self.form_class = EmailNotificationForm
        elif self.n_type == "pushover":
            LOGGER.debug("get pushover form")
            self.model = PushoverNotification
            self.form_class = PushoverNotificationForm

        return super().dispatch(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["n_type"] = self.n_type
        return context


class NotificationUpdateView(NotificationBaseView, UpdateView):
    """notification create view - handle parse errors"""

    template_name = "borghive/notification_update.html"
    success_url = reverse_lazy("notification-list")

    def dispatch(self, *args, **kwargs):
        """get notification type and init form of this type"""
        obj = Notification.objects.get(id=kwargs["pk"])
        self.model = obj._meta.model
        self.form_class = getattr(borghive.forms, obj.form_class, None)
        return super().dispatch(*args, **kwargs)


class NotificationTestView(View, SingleObjectMixin):
    """notification test view - handle parse errors"""

    # pylint: disable=broad-except,unused-argument

    model = Notification
    object = None

    def get(self, *args, **kwargs):
        """send test notification"""
        message = None
        try:
            self.object = self.get_object(
                queryset=self.model.objects.filter(id=kwargs["pk"])
            )
            self.object.notify(**self.object.get_test_params())
            message = f"Sent {self.object}"
        except self.model.DoesNotExist:
            message = "Notification not found."
        except SMTPException as e:
            LOGGER.error("SMTP error during test notification: %s", e)
            message = f"Test failed due to email error: {e}"
        except requests.exceptions.RequestException as e:
            LOGGER.error("Network error during test notification: %s", e)
            message = f"Test failed due to network error: {e}"
        except Exception as e:
            LOGGER.error("Unexpected error during test notification: %s", e)
            message = f"Test failed: {e}"

        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            # Return HTML for modal display
            return render(
                self.request, "borghive/notification_test.html", {"message": message}
            )

        # Redirect with message for non-modal requests
        if "Sent" in message:
            messages.add_message(self.request, messages.SUCCESS, message)
        else:
            messages.add_message(self.request, messages.ERROR, message)
        return redirect(reverse("notification-list"))
