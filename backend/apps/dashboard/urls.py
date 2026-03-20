from django.urls import path
from .views import DashboardStatsView, RecentDocumentsView, MyTasksView

urlpatterns = [
    path("stats/", DashboardStatsView.as_view()),
    path("recent_documents/", RecentDocumentsView.as_view()),
    path("my_tasks/", MyTasksView.as_view()),
]
