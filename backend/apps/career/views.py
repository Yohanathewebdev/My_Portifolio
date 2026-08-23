from rest_framework import mixins
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import Achievement, Certification, Education, Experience, Skill
from .serializers import AchievementSerializer, CertificationSerializer, EducationSerializer, ExperienceSerializer, SkillSerializer


class CareerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, AccountScopedViewSet):
    permission_classes = [CreateEditPermission]

    def get_portfolio(self):
        from apps.portfolios.models import Portfolio

        return Portfolio.objects.for_accounts(self.get_accounts()).get(pk=self.kwargs["portfolio_id"])

    def get_queryset(self):
        return self.queryset.objects.for_portfolio(self.get_portfolio())

    def perform_create(self, serializer):
        model = self.get_serializer_class().Meta.model
        serializer.instance = model.objects.create_for_portfolio(
            self.get_portfolio(), **serializer.validated_data
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        expected = request.headers.get("If-Match") or request.data.get("version")
        if expected is None or int(expected) != instance.version:
            raise ConflictError(current_version=instance.version, expected_version=int(expected or 0))
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        serializer.save(version=instance.version + 1)
        return Response(self.get_serializer(instance).data)


class ExperienceViewSet(CareerViewSet):
    serializer_class, queryset = ExperienceSerializer, Experience


class EducationViewSet(CareerViewSet):
    serializer_class, queryset = EducationSerializer, Education


class SkillViewSet(CareerViewSet):
    serializer_class, queryset = SkillSerializer, Skill


class CertificationViewSet(CareerViewSet):
    serializer_class, queryset = CertificationSerializer, Certification


class AchievementViewSet(CareerViewSet):
    serializer_class, queryset = AchievementSerializer, Achievement
