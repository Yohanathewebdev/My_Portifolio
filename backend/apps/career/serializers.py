from rest_framework import serializers

from apps.content.rich_text import sanitize_html

from .models import Achievement, Certification, Education, Experience, Skill


class CareerSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        if "description_html" in attrs:
            attrs["description_html"] = sanitize_html(attrs["description_html"])
        return attrs

    class Meta:
        abstract = True
        read_only_fields = ["id", "portfolio", "version"]


class ExperienceSerializer(CareerSerializer):
    class Meta(CareerSerializer.Meta):
        model = Experience
        fields = "__all__"


class EducationSerializer(CareerSerializer):
    class Meta(CareerSerializer.Meta):
        model = Education
        fields = "__all__"


class SkillSerializer(CareerSerializer):
    class Meta(CareerSerializer.Meta):
        model = Skill
        fields = "__all__"


class CertificationSerializer(CareerSerializer):
    class Meta(CareerSerializer.Meta):
        model = Certification
        fields = "__all__"


class AchievementSerializer(CareerSerializer):
    class Meta(CareerSerializer.Meta):
        model = Achievement
        fields = "__all__"
