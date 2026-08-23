from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.portfolios.models import Portfolio
from .serializers import PublicPortfolioSerializer


class PublicPortfolioDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicPortfolioSerializer
    # Use publication_state instead of is_published, and _base_manager to bypass tenant scoping
    queryset = Portfolio._base_manager.filter(publication_state="published")
    lookup_field = "slug"