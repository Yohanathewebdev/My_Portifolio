from rest_framework import serializers

from apps.content.rich_text import sanitize_html

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "id", "portfolio", "full_name", "headline", "biography_html", "biography_editor_json",
            "avatar_id", "email", "phone", "city", "country", "timezone", "social_links",
            "available_for_work", "open_to_relocation", "version",
        ]
        read_only_fields = ["id", "portfolio", "version"]

    def validate_biography_html(self, value):
        return sanitize_html(value)
