from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from apps.content.views import ArticleViewSet, MediaAssetViewSet
from apps.projects.views import ProjectViewSet
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
from apps.public.views import PublicPortfolioDetailView

from apps.career.views import AchievementViewSet, CertificationViewSet, EducationViewSet, ExperienceViewSet, SkillViewSet
from apps.profiles.views import ProfileViewSet
from apps.professionals.views import PortfolioProfessionViewSet, ProfessionViewSet
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
router.register("professions", ProfessionViewSet, basename="profession")

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
    path("public/portfolios/<slug:slug>/", PublicPortfolioDetailView.as_view(), name="public-portfolio-detail"),
    path(
        "api/portfolios/<uuid:portfolio_id>/profile/",
        ProfileViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"}),
        name="profile-detail",
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/professions/",
        PortfolioProfessionViewSet.as_view({"get": "list", "post": "create"}),
        name="portfolio-profession-list",
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/professions/<uuid:pk>/",
        PortfolioProfessionViewSet.as_view({"delete": "destroy", "patch": "partial_update"}),
        name="portfolio-profession-detail",
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/experiences/",
        ExperienceViewSet.as_view({"get": "list", "post": "create"}), name="experience-list"
    ),
    path("api/portfolios/<uuid:portfolio_id>/experiences/<uuid:pk>/", ExperienceViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="experience-detail"),
    path("api/portfolios/<uuid:portfolio_id>/education/", EducationViewSet.as_view({"get": "list", "post": "create"}), name="education-list"),
    path("api/portfolios/<uuid:portfolio_id>/education/<uuid:pk>/", EducationViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="education-detail"),
    path("api/portfolios/<uuid:portfolio_id>/skills/", SkillViewSet.as_view({"get": "list", "post": "create"}), name="skill-list"),
    path("api/portfolios/<uuid:portfolio_id>/skills/<uuid:pk>/", SkillViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="skill-detail"),
    path("api/portfolios/<uuid:portfolio_id>/certifications/", CertificationViewSet.as_view({"get": "list", "post": "create"}), name="certification-list"),
    path("api/portfolios/<uuid:portfolio_id>/certifications/<uuid:pk>/", CertificationViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="certification-detail"),
    path("api/portfolios/<uuid:portfolio_id>/achievements/", AchievementViewSet.as_view({"get": "list", "post": "create"}), name="achievement-list"),
    path("api/portfolios/<uuid:portfolio_id>/achievements/<uuid:pk>/", AchievementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="achievement-detail"),
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/schema/", PublicSchemaView.as_view(), name="schema"),
    path("api/docs/", PublicSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "api/portfolios/<uuid:portfolio_id>/articles/",
        ArticleViewSet.as_view({"get": "list", "post": "create"}), 
        name="article-list"
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/articles/<uuid:pk>/", 
        ArticleViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), 
        name="article-detail"
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/articles/<uuid:pk>/publish/", 
        ArticleViewSet.as_view({"post": "publish"}), 
        name="article-publish"
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/media/",
        MediaAssetViewSet.as_view({"get": "list", "post": "create"}), 
        name="media-list"
    ),
    path(
        "api/portfolios/<uuid:portfolio_id>/media/<uuid:pk>/", 
        MediaAssetViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), 
        name="media-detail"
    ),
    path(
            "api/portfolios/<uuid:portfolio_id>/projects/",
            ProjectViewSet.as_view({"get": "list", "post": "create"}),
            name="project-list",
        ),
        path(
            "api/portfolios/<uuid:portfolio_id>/projects/<uuid:pk>/",
            ProjectViewSet.as_view(
                {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
            ),
            name="project-detail",
        ),
        path(
            "api/portfolios/<uuid:portfolio_id>/projects/<uuid:pk>/publish/",
            ProjectViewSet.as_view({"post": "publish"}),
            name="project-publish",
        ),
        path(
            "api/portfolios/<uuid:portfolio_id>/projects/<uuid:pk>/unpublish/",
            ProjectViewSet.as_view({"post": "unpublish"}),
            name="project-unpublish",
        ),
]
