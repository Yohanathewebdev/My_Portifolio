from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import PortfolioProfession, Profession
from .serializers import PortfolioProfessionSerializer, ProfessionSerializer


class ProfessionViewSet(mixins.ListModelMixin, AccountScopedViewSet):
    serializer_class = ProfessionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Profession.objects.none()

    def get_queryset(self):
        return Profession.objects.filter(is_active=True)


class PortfolioProfessionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    AccountScopedViewSet,
):
    serializer_class = PortfolioProfessionSerializer
    permission_classes = [CreateEditPermission]
    queryset = PortfolioProfession.objects.none()

    def get_portfolio(self):
        from apps.portfolios.models import Portfolio

        return Portfolio.objects.for_accounts(self.get_accounts()).get(pk=self.kwargs["portfolio_id"])

    def get_queryset(self):
        return PortfolioProfession.objects.filter(portfolio=self.get_portfolio())

    def perform_create(self, serializer):
        serializer.save(portfolio=self.get_portfolio())
