"""
Diagnosis URL patterns — design_doc §4.3
Mounted at /api/v1/diagnosis/ in config/urls.py

Phase 2 routes (all active):
  POST/GET  /                       → list + submit
  GET       /{diagnosis_id}/        → detail / polling
  PATCH     /{diagnosis_id}/opinion/ → submit doctor opinion + trigger PDF
  GET       /{diagnosis_id}/report/  → Pre-signed PDF URL
"""
from django.urls import path

from apps.diagnosis.views.diagnosis_views import (
    DiagnosisDetailView,
    DiagnosisListCreateView,
)
from apps.diagnosis.views.opinion_views import DiagnosisOpinionView
from apps.diagnosis.views.report_views import DiagnosisReportView

urlpatterns = [
    # POST /api/v1/diagnosis/   → submit (Clinician only)
    # GET  /api/v1/diagnosis/   → list (role-filtered)
    path("", DiagnosisListCreateView.as_view(), name="diagnosis-list-create"),

    # GET /api/v1/diagnosis/{diagnosis_id}/   → detail / polling
    path("<uuid:diagnosis_id>/", DiagnosisDetailView.as_view(), name="diagnosis-detail"),

    # PATCH /api/v1/diagnosis/{diagnosis_id}/opinion/   → submit doctor opinion
    path("<uuid:diagnosis_id>/opinion/", DiagnosisOpinionView.as_view(), name="diagnosis-opinion"),

    # GET /api/v1/diagnosis/{diagnosis_id}/report/   → Pre-signed PDF URL
    path("<uuid:diagnosis_id>/report/", DiagnosisReportView.as_view(), name="diagnosis-report"),
]
