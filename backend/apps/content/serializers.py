from rest_framework import serializers

from .models import Article, MediaAsset
from .rich_text import sanitize_html


class ArticleSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        # Apply strict server-side HTML sanitization
        if "body_html" in attrs:
            attrs["body_html"] = sanitize_html(attrs["body_html"])
        return attrs

    class Meta:
        model = Article
        fields = "__all__"
        # Protect system-managed fields from manual manipulation
        read_only_fields = ["id", "portfolio", "version", "status", "published_at"]


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = "__all__"
        read_only_fields = ["id", "portfolio"]