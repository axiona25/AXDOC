from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowTemplateViewSet, WorkflowInstanceViewSet, WorkflowStepViewSet

router = DefaultRouter()
router.register(r"templates", WorkflowTemplateViewSet, basename="workflowtemplate")
router.register(r"instances", WorkflowInstanceViewSet, basename="workflowinstance")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "templates/<uuid:template_pk>/steps/",
        WorkflowStepViewSet.as_view({"get": "list", "post": "create"}),
        name="workflowstep-list",
    ),
    path(
        "templates/<uuid:template_pk>/steps/<uuid:pk>/",
        WorkflowStepViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}),
        name="workflowstep-detail",
    ),
]
