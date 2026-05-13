"""
Admin user-management URL patterns — design_doc §4.4
Mounted at /api/v1/users/ in config/urls.py
"""
from django.urls import path

from apps.authentication.admin_views import UserDetailView, UserListCreateView

urlpatterns = [
    # GET /api/v1/users/    POST /api/v1/users/
    path("", UserListCreateView.as_view(), name="user-list-create"),

    # GET /api/v1/users/{id}/   PUT /api/v1/users/{id}/   DELETE /api/v1/users/{id}/
    path("<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
]
