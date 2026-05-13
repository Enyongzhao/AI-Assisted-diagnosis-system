"""
Authentication URL patterns — design_doc §4.1
Mounted at /api/v1/auth/ in config/urls.py
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.authentication.views import LoginView

urlpatterns = [
    # design_doc §4.1 POST /api/v1/auth/login/
    path("login/", LoginView.as_view(), name="auth-login"),

    # design_doc §4.1 POST /api/v1/auth/refresh/
    # simplejwt's built-in view handles { "refresh": "..." } → { "access": "..." }
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
]
