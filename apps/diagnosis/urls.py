"""
Diagnosis URL patterns — design_doc §4.3
Mounted at /api/v1/diagnosis/ in config/urls.py

Phase 1:  POST + GET /   GET /{id}/
Phase 2:  PATCH /{id}/opinion/   GET /{id}/report/   (added in Phase 2)
"""
from django.urls import path

from apps.diagnosis.views.diagnosis_views import (
    DiagnosisDetailView,
    DiagnosisListCreateView,
)

urlpatterns = [
    # POST /api/v1/diagnosis/   → submit (Clinician only)
    # GET  /api/v1/diagnosis/   → list (role-filtered)
    path("", DiagnosisListCreateView.as_view(), name="diagnosis-list-create"),

    # GET /api/v1/diagnosis/{diagnosis_id}/   → detail / polling
    path("<uuid:diagnosis_id>/", DiagnosisDetailView.as_view(), name="diagnosis-detail"),

    # Phase 2 additions — uncomment when views are implemented:
    # path("<uuid:diagnosis_id>/opinion/", DiagnosisOpinionView.as_view(), name="diagnosis-opinion"),
    # path("<uuid:diagnosis_id>/report/",  DiagnosisReportView.as_view(),  name="diagnosis-report"),
]
