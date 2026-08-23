from __future__ import annotations

from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.core.permissions import CreateEditPermission
from apps.core.views import AccountScopedViewSet

from .models import Project, Tag
from .serializers import ProjectSerializer

# This duplicates ~40 lines of apps.content.views.ContentViewSet
# (get_portfolio, the OCC-aware update(), get_queryset) rather than
# importing that class directly. Reasoning: ContentViewSet lives in the
# `content` app, and having `projects` import view internals from an
# unrelated content-type app would be a real coupling, not a convenience
# â€” the design doc's app boundaries (Â§5.1) treat these as separate
# domains. If a third app needs this same shape, that's the point to
# extract a shared base into apps.core.views â€” not before.
#
# permission_classes = [CreateEditPermission] applied uniformly to every
# action (including list/retrieve) mirrors ContentViewSet exactly. Note
# this means viewer-role users can't even read drafts through this
# endpoint, despite ROLE_MATRIX having a distinct "read_draft" row that
# permits it. That's true of ArticleViewSet too, as shown â€” not something
# introduced here. Worth deciding deliberately whether that's intended
# platform-wide, rather than each new app quietly inheriting the gap.


class ProjectViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    AccountScopedViewSet,
):
    serializer_class = ProjectSerializer
    permission_classes = [CreateEditPermission]
    queryset = Project

    def get_portfolio(self):
        from apps.portfolios.models import Portfolio

        return Portfolio.objects.for_accounts(self.get_accounts()).get(
            pk=self.kwargs["portfolio_id"]
        )

    def get_queryset(self):
        return self.queryset.objects.for_portfolio(self.get_portfolio())

    def perform_create(self, serializer):
        model = self.get_serializer_class().Meta.model
        tag_names = serializer.validated_data.pop("tag_names", [])
        portfolio = self.get_portfolio()
        project = model.objects.create_for_portfolio(
            portfolio, **serializer.validated_data
        )
        if tag_names:
            _attach_tags(project, portfolio, tag_names)
        serializer.instance = project

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if hasattr(instance, "version"):
            expected = request.headers.get("If-Match") or request.data.get("version")
            if expected is None or int(expected) != instance.version:
                raise ConflictError(
                    current_version=instance.version, expected_version=int(expected or 0)
                )

        tag_names = request.data.get("tag_names")
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("tag_names", None)

        if hasattr(instance, "version"):
            serializer.save(version=instance.version + 1)
        else:
            serializer.save()

        if tag_names is not None:
            _attach_tags(instance, self.get_portfolio(), tag_names, replace=True)

        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, *args, **kwargs):
        """Mirrors ArticleViewSet.publish() exactly, including the
        already-published 400 guard."""
        project = self.get_object()
        if project.publication_state == Project.STATE_PUBLISHED:
            return Response(
                {"detail": "Project is already published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.publish(actor=request.user)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, *args, **kwargs):
        project = self.get_object()
        project.unpublish(actor=request.user)
        return Response(self.get_serializer(project).data)


def _attach_tags(project, portfolio, names, *, replace=False):
    tags = []
    for name in names:
        slug = name.strip().lower().replace(" ", "-")[:70]
        tag, _ = Tag.objects.get_or_create(
            portfolio=portfolio, slug=slug, defaults={"name": name.strip()}
        )
        tags.append(tag)
    if replace:
        project.tags.set(tags)
    else:
        project.tags.add(*tags)

