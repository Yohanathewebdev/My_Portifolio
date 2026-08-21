from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.health import healthz, readyz
from apps.core.scoping import SCOPING_ALLOWLIST

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Explicitly expose the reviewed non-portfolio routes to the scoping meta-test.
SCOPING_ALLOWLIST = SCOPING_ALLOWLIST
