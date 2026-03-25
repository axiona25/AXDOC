from django.urls import path
from .views import (
    DashboardStatsView,
    DocumentsTrendView,
    MyTasksView,
    ProtocolsTrendView,
    RecentDocumentsView,
    StorageTrendView,
    WorkflowStatsView,
)

urlpatterns = [
    path("stats/", DashboardStatsView.as_view()),
    path("recent_documents/", RecentDocumentsView.as_view()),
    path("my_tasks/", MyTasksView.as_view()),
    path("documents_trend/", DocumentsTrendView.as_view(), name="documents-trend"),
    path("protocols_trend/", ProtocolsTrendView.as_view(), name="protocols-trend"),
    path("workflow_stats/", WorkflowStatsView.as_view(), name="workflow-stats"),
    path("storage_trend/", StorageTrendView.as_view(), name="storage-trend"),
]
