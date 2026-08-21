from django.db import models

from apps.core.models import PortfolioOwnedModel


class ScopedRecord(PortfolioOwnedModel):
    """Concrete test model that exercises the real scoped ORM integration."""

    name = models.CharField(max_length=100)
