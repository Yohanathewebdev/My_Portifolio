# Not a real urls.py — this app has no independent URL root, exactly like
# `career`. Add these lines into the main `urls.py` you shared earlier,
# alongside the existing career/profile/profession paths, and add the
# import at the top:
#
#   from apps.projects.views import ProjectViewSet
#
# then insert into urlpatterns:

"""
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
"""
