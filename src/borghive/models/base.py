from django.db import models

from rules.contrib.models import RulesModelBase, RulesModelMixin


# pylint: disable=too-few-public-methods
class BaseModel(RulesModelMixin, models.Model, metaclass=RulesModelBase):
    """base model for all borghive models"""

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
