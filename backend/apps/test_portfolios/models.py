import uuid

from django.db import models


class Portfolio(models.Model):
    """Test-only target for the core lazy portfolio foreign key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "portfolios"

    def __str__(self) -> str:
        return self.name
