from django.db import models

from apps.core.models import BaseModel


class Profile(BaseModel):
    portfolio = models.OneToOneField("portfolios.Portfolio", on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=200, blank=True)
    headline = models.CharField(max_length=250, blank=True)
    biography_html = models.TextField(blank=True)
    biography_editor_json = models.JSONField(default=dict, blank=True)
    avatar_id = models.UUIDField(null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    social_links = models.JSONField(default=list, blank=True)
    available_for_work = models.BooleanField(default=False)
    open_to_relocation = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
