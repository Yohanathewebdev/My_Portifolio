from rest_framework import mixins
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import Profile
from .serializers import ProfileSerializer


class ProfileViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, AccountScopedViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [CreateEditPermission]
    queryset = Profile.objects.none()

    def get_portfolio(self):
        from apps.portfolios.models import Portfolio

        return Portfolio.objects.for_accounts(self.get_accounts()).get(pk=self.kwargs["portfolio_id"])

    def get_object(self):
        profile, _ = Profile.objects.get_or_create(portfolio=self.get_portfolio())
        return profile

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        expected = request.headers.get("If-Match") or request.data.get("version")
        if expected is None or int(expected) != profile.version:
            raise ConflictError(current_version=profile.version, expected_version=int(expected or 0))
        serializer = self.get_serializer(profile, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        serializer.save(version=profile.version + 1)
        return Response(self.get_serializer(profile).data)
