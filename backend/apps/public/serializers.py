from rest_framework import serializers

from apps.portfolios.models import Portfolio
from apps.profiles.models import Profile


class PublicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["headline", "bio", "avatar_url", "location", "website", "social_links"]


class PublicPortfolioSerializer(serializers.ModelSerializer):
    profile = PublicProfileSerializer(read_only=True)
    professions = serializers.SerializerMethodField()
    experiences = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    certifications = serializers.SerializerMethodField()
    achievements = serializers.SerializerMethodField()
    projects = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            "id", "name", "slug", "custom_domain", "is_published",
            "profile", "professions", "experiences", "education",
            "skills", "certifications", "achievements", "projects", "articles"
        ]

    def get_professions(self, obj):
        return [p.profession.name for p in obj.professions.all()]

    def get_experiences(self, obj):
        return list(obj.experiences.values(
            "id", "title", "company", "location", "start_date", "end_date", "is_current", "description"
        ))

    def get_education(self, obj):
        return list(obj.education.values(
            "id", "institution", "degree", "field_of_study", "start_date", "end_date", "description"
        ))

    def get_skills(self, obj):
        return list(obj.skills.values("id", "name", "proficiency", "category"))

    def get_certifications(self, obj):
        return list(obj.certifications.values(
            "id", "name", "issuing_organization", "issue_date", "expiry_date", "credential_id", "credential_url"
        ))

    def get_achievements(self, obj):
        return list(obj.achievements.values("id", "title", "date", "description", "url"))

    def get_projects(self, obj):
        return list(obj.projects.filter(status="published").values(
            "id", "title", "slug", "summary", "body_html", "repo_url", "live_url", "thumbnail_url"
        ))

    def get_articles(self, obj):
        return list(obj.articles.filter(status="published").values(
            "id", "title", "slug", "summary", "body_html", "published_at"
        ))