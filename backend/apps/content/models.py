from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import PortfolioOwnedModel
from .rich_text import sanitize_html


class Article(PortfolioOwnedModel):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    summary = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    body_editor_json = models.JSONField(default=dict, blank=True)
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="draft",
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)  # Optimistic concurrency lock

    class Meta:
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "slug"], 
                name="unique_article_slug_per_portfolio"
            )
        ]

    def save(self, *args, **kwargs):
        # Sanitize HTML using your custom HTMLParser before it hits the database
        if self.body_html:
            self.body_html = sanitize_html(self.body_html)
            
        # Auto-generate a slug if one isn't provided
        if not self.slug:
            self.slug = slugify(self.title)
            
        super().save(*args, **kwargs)

    def publish(self):
        self.status = "published"
        self.published_at = timezone.now()
        self.save()

    def __str__(self):
        return self.title


class MediaAsset(PortfolioOwnedModel):
    file_key = models.CharField(max_length=512)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    mime_type = models.CharField(max_length=100)
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.file_name