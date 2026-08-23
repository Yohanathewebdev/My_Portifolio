from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import PortfolioOwnedModel


class OrderedVisibleModel(PortfolioOwnedModel):
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class Experience(OrderedVisibleModel):
    title = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description_html = models.TextField(blank=True)
    description_editor_json = models.JSONField(default=dict, blank=True)
    highlights = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["sort_order", "-start_date"]


class Education(OrderedVisibleModel):
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    grade = models.CharField(max_length=100, blank=True)
    description_html = models.TextField(blank=True)
    description_editor_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "-end_date"]


class Skill(OrderedVisibleModel):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=100, blank=True)
    proficiency = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "name"]


class Certification(OrderedVisibleModel):
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)

    class Meta:
        ordering = ["sort_order", "-issue_date"]


class Achievement(OrderedVisibleModel):
    title = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, blank=True)
    date = models.DateField(null=True, blank=True)
    description_html = models.TextField(blank=True)
    description_editor_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["sort_order", "-date"]
