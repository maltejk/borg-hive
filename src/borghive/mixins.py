from django.db.models import Q
from django.views.generic.edit import DeleteView


class OwnerFilterMixin:
    """mixin to filter querysets for owner"""

    def get_queryset(self):
        """get only objects related to owner or same group"""
        return (
            super()
            .get_queryset()
            .filter(
                Q(owner=self.request.user) | Q(group__in=self.request.user.groups.all())
            )
        )

    def get_form_kwargs(self):
        """pass owner to forms"""
        kwargs = super().get_form_kwargs()
        if not isinstance(self, DeleteView):
            # DeleteView's default form is a plain Form, not a ModelForm,
            # and doesn't accept the extra "owner" kwarg
            kwargs.update({"owner": self.request.user})
        return kwargs
