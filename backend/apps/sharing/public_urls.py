"""
URL accesso pubblico condivisione (no autenticazione).
"""
from django.urls import path
from .views import PublicShareView, PublicShareVerifyPasswordView, PublicShareDownloadView

urlpatterns = [
    path("<str:token>/", PublicShareView.as_view(), name="public-share"),
    path("<str:token>/verify_password/", PublicShareVerifyPasswordView.as_view(), name="public-share-verify-password"),
    path("<str:token>/download/", PublicShareDownloadView.as_view(), name="public-share-download"),
]
