"""
Patient URL patterns — design_doc §4.2
Mounted at /api/v1/patients/ in config/urls.py
"""
from django.urls import path

from apps.patients.views import PatientDetailView, PatientListCreateView

urlpatterns = [
    # POST /api/v1/patients/   GET /api/v1/patients/
    path("", PatientListCreateView.as_view(), name="patient-list-create"),

    # GET /api/v1/patients/{id}/   PUT /api/v1/patients/{id}/   DELETE /api/v1/patients/{id}/
    path("<int:patient_id>/", PatientDetailView.as_view(), name="patient-detail"),
]
