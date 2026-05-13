"""
Root URL configuration — design_doc §4 base path /api/v1/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),

    # design_doc §4.1 — Authentication endpoints
    path("api/v1/auth/", include("apps.authentication.urls")),

    # design_doc §4.2 — Patient management
    path("api/v1/patients/", include("apps.patients.urls")),

    # design_doc §4.3 — Diagnosis jobs (core)
    path("api/v1/diagnosis/", include("apps.diagnosis.urls")),

    # design_doc §4.4 — User management (Admin only)
    path("api/v1/users/", include("apps.authentication.admin_urls")),
]

# Serve generated PDF reports from media/ in local dev (DEBUG=True only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
