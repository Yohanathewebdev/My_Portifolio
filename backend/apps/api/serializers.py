from uuid import UUID

from rest_framework import serializers

from apps.accounts.models import Account, AccountMembership, User
from apps.portfolios.models import Portfolio, PortfolioSlugHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_email_verified"]
        read_only_fields = fields


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "name", "slug", "status", "billing_email", "country_code"]
        read_only_fields = fields


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AccountMembership
        fields = ["id", "user", "email", "role", "invited_at", "accepted_at"]
        read_only_fields = ["id", "user", "email", "invited_at", "accepted_at"]


class MembershipInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=AccountMembership.ROLE_CHOICES)


class PortfolioSerializer(serializers.ModelSerializer):
    def validate_slug(self, value):
        if Portfolio.all_objects.filter(slug=value).exists():
            instance = getattr(self, "instance", None)
            if instance is None or instance.slug != value:
                raise serializers.ValidationError("A portfolio already uses this slug.")
        history = PortfolioSlugHistory.objects.filter(old_slug=value)
        instance_id = getattr(self.instance, "pk", None)
        if isinstance(instance_id, UUID):
            history = history.exclude(portfolio_id=instance_id)
        if history.exists():
            raise serializers.ValidationError("This slug was previously used by another portfolio.")
        return value

    class Meta:
        model = Portfolio
        fields = [
            "id",
            "account",
            "slug",
            "title",
            "publication_state",
            "published_at",
            "unpublished_at",
            "primary_locale",
            "default_currency",
            "seo_title",
            "seo_description",
            "is_indexable",
        ]
        read_only_fields = [
            "id",
            "account",
            "publication_state",
            "published_at",
            "unpublished_at",
        ]
        extra_kwargs: dict[str, dict[str, list]] = {"slug": {"validators": []}}
