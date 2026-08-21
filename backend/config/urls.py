from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.accounts.auth_views import (
    CsrfTokenView,
    LoginTwoFactorView,
    LoginView,
    LogoutAllView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RecoveryCodesRegenerateView,
    RefreshView,
    SessionListView,
    SessionRevokeView,
    SignupView,
    TotpConfirmView,
    TotpDisableView,
    TotpSetupView,
    VerificationConfirmView,
    VerificationRequestView,
)
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
    path("api/auth/csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
    path("api/auth/signup/", SignupView.as_view(), name="auth-signup"),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/login/2fa/", LoginTwoFactorView.as_view(), name="auth-login-2fa"),
    path("api/auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/logout-all/", LogoutAllView.as_view(), name="auth-logout-all"),
    path("api/auth/sessions/", SessionListView.as_view(), name="auth-sessions"),
    path(
        "api/auth/sessions/<uuid:session_id>/revoke/",
        SessionRevokeView.as_view(),
        name="auth-session-revoke",
    ),
    path(
        "api/auth/verification/request/",
        VerificationRequestView.as_view(),
        name="auth-verification-request",
    ),
    path(
        "api/auth/verification/confirm/",
        VerificationConfirmView.as_view(),
        name="auth-verification-confirm",
    ),
    path("api/auth/password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
    path(
        "api/auth/password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "api/auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("api/auth/2fa/setup/", TotpSetupView.as_view(), name="auth-2fa-setup"),
    path("api/auth/2fa/confirm/", TotpConfirmView.as_view(), name="auth-2fa-confirm"),
    path("api/auth/2fa/disable/", TotpDisableView.as_view(), name="auth-2fa-disable"),
    path(
        "api/auth/2fa/recovery-codes/",
        RecoveryCodesRegenerateView.as_view(),
        name="auth-2fa-recovery-codes",
    ),
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
