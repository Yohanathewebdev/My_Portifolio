from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import Article, MediaAsset
from .serializers import ArticleSerializer, MediaAssetSerializer


class ContentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    AccountScopedViewSet,
):
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
        
        # Enforce Optimistic Concurrency Control (OCC) if the model supports it
        if hasattr(instance, "version"):
            expected = request.headers.get("If-Match") or request.data.get("version")
            if expected is None or int(expected) != instance.version:
                raise ConflictError(
                    current_version=instance.version, expected_version=int(expected or 0)
                )
                
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        
        if hasattr(instance, "version"):
            serializer.save(version=instance.version + 1)
        else:
            serializer.save()
            
        return Response(self.get_serializer(instance).data)


class ArticleViewSet(ContentViewSet):
    serializer_class = ArticleSerializer
    queryset = Article

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        """Custom endpoint to transition an article from draft to published."""
        article = self.get_object()
        
        if article.status == "published":
            return Response(
                {"detail": "Article is already published."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        article.publish()
        return Response(self.get_serializer(article).data)


class MediaAssetViewSet(ContentViewSet):
    serializer_class = MediaAssetSerializer
    queryset = MediaAsset