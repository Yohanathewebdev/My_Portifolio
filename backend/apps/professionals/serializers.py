from rest_framework import serializers

from .models import PortfolioProfession, Profession


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = ["id", "name", "slug", "category", "description", "icon", "suggestion_config"]
        read_only_fields = fields


class PortfolioProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioProfession
        fields = ["id", "portfolio", "profession", "is_primary", "display_order"]
        read_only_fields = ["id", "portfolio"]
