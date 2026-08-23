from __future__ import annotations

from rest_framework import serializers

from apps.content.models import MediaAsset

from .models import Project, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        read_only_fields = ["id", "slug"]


class ProjectSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=60),
        write_only=True,
        required=False,
        help_text="Tag names; tags are get-or-created per portfolio.",
    )

    # NOTE: queryset is MediaAsset.all_objects (the unscoped manager), not
    # MediaAsset.objects (PortfolioScopedManager) â€” the latter would raise
    # UnscopedQueryError immediately, since a serializer field's queryset
    # is built with no portfolio in scope. That means this field alone
    # does NOT prevent attaching another portfolio's MediaAsset â€” that
    # check lives in Project.clean() instead (see models.py). Don't remove
    # the model-level check on the assumption this field already covers it.
    cover_image = serializers.PrimaryKeyRelatedField(
        queryset=MediaAsset.all_objects.all(), required=False, allow_null=True
    )

    # Exposed read-only so clients can send it back as If-Match / body
    # `version` on update, per ContentViewSet.update()'s OCC check.
    version = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "description_editor_json",
            "summary",
            "client",
            "role",
            "start_date",
            "end_date",
            "cover_image",
            "tags",
            "tag_names",
            "links",
            "is_featured",
            "sort_order",
            "publication_state",
            "published_at",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "publication_state",
            "published_at",
            "version",
            "created_at",
            "updated_at",
        ]

    def validate_links(self, value):
        for link in value:
            if not isinstance(link, dict) or "url" not in link:
                raise serializers.ValidationError("each link requires a 'url' key")
        return value

