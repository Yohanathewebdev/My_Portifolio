from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    AccountViewSet,
    CurrentUserViewSet,
    MembershipViewSet,
    PortfolioViewSet,
)
from apps.core.health import healthz, readyz
from apps.core.views import PublicReadOnlyView


class PublicSchemaView(PublicReadOnlyView, SpectacularAPIView):  # type: ignore[misc]
    pass


class PublicSwaggerView(PublicReadOnlyView, SpectacularSwaggerView):  # type: ignore[misc]
    pass


router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="account")
router.register("me", CurrentUserViewSet, basename="me")
router.register("portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("api/", include(router.urls)),
    path(
        "api/accounts/<uuid:account_id>/members/",
        MembershipViewSet.as_view({"get": "list", "post": "create"}),
        name="membership-list",
    ),
    path(
        "api/accounts/<uuid:account_id>/members/<uuid:pk>/",
        MembershipViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="membership-detail",
    ),
    path(
        "api/accounts/<uuid:account_id>/members/<uuid:pk>/role/",
        MembershipViewSet.as_view({"patch": "role"}),
        name="membership-role",
    ),
    path(
        "api/accounts/<uuid:account_id>/members/<uuid:pk>/transfer-ownership/",
        MembershipViewSet.as_view({"post": "transfer_ownership"}),
        name="membership-transfer-ownership",
    ),
    path(
        "api/accounts/<uuid:account_id>/portfolios/",
        PortfolioViewSet.as_view({"get": "list", "post": "create"}),
        name="portfolio-list",
    ),
    path(
        "api/accounts/<uuid:account_id>/portfolios/<uuid:pk>/",
        PortfolioViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="portfolio-detail",
    ),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/schema/", PublicSchemaView.as_view(), name="schema"),
    path("api/docs/", PublicSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
