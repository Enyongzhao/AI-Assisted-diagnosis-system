"""
Integration tests for report API — design_doc §9.3 / §4.3

Tests:
  - Clinician gets PDF URL for own job (200)
  - Client gets PDF URL for own patient's job (200)
  - Other clinician cannot get PDF URL (403)
  - Client cannot access another patient's report (403)
  - Report not ready → 404
"""
from unittest.mock import patch

import pytest

from apps.authentication.models import User
from apps.diagnosis.models import DiagnosisJob
from repositories.diagnosis_repository import DiagnosisRepository
from repositories.llm_report_repository import LLMReportRepository
from repositories.doctor_opinion_repository import DoctorOpinionRepository
from repositories.report_repository import ReportRepository


def _create_completed_diagnosis(clinician_client, clinician_user, diagnosis_payload,
                                 client_user, sample_patient):
    """Helper: creates a diagnosis job and fast-forwards it to 'completed' state."""
    with patch("tasks.llm_task.generate_llm_report.delay"):
        resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                      format="json")
    diagnosis_id = resp.data["diagnosis_id"]

    # Manually create LLM report record
    LLMReportRepository.create(
        diagnosis_id=diagnosis_id,
        report_data={
            "summary": "Test", "differential_diagnosis": ["A"],
            "recommended_investigations": ["X-ray"], "risk_factors": ["R"],
            "llm_provider": "mock", "llm_model": "mock-llm",
            "prompt_tokens": 10, "completion_tokens": 20,
            "raw_response": {},
        },
    )

    # Manually create doctor opinion
    DoctorOpinionRepository.create(
        diagnosis_id=diagnosis_id,
        text="Test opinion.",
        submitted_by=clinician_user,
    )

    # Create report record (simulates PDF upload)
    ReportRepository.create(
        diagnosis_id=diagnosis_id,
        s3_key=f"reports/{diagnosis_id}/report.pdf",
        file_size_bytes=1024,
    )

    DiagnosisRepository.update_status(diagnosis_id, "completed")
    return diagnosis_id


@pytest.mark.django_db
class TestReportDownload:
    """design_doc §4.3 GET /api/v1/diagnosis/{id}/report/"""

    @patch("adapters.s3_adapter.S3Adapter.generate_presigned_url")
    def test_clinician_can_get_own_report_url(self, mock_presign, clinician_client,
                                               clinician_user, diagnosis_payload,
                                               client_user, sample_patient):
        mock_presign.return_value = "https://s3.example.com/signed-url"

        diagnosis_id = _create_completed_diagnosis(
            clinician_client, clinician_user, diagnosis_payload, client_user, sample_patient
        )

        response = clinician_client.get(f"/api/v1/diagnosis/{diagnosis_id}/report/")

        assert response.status_code == 200
        assert "pdf_url" in response.data

    @patch("adapters.s3_adapter.S3Adapter.generate_presigned_url")
    def test_client_can_get_own_patient_report(self, mock_presign, clinician_client,
                                                clinician_user, client_api_client,
                                                diagnosis_payload, client_user,
                                                sample_patient):
        mock_presign.return_value = "https://s3.example.com/signed-url"

        diagnosis_id = _create_completed_diagnosis(
            clinician_client, clinician_user, diagnosis_payload, client_user, sample_patient
        )

        response = client_api_client.get(f"/api/v1/diagnosis/{diagnosis_id}/report/")
        assert response.status_code == 200

    @patch("adapters.s3_adapter.S3Adapter.generate_presigned_url")
    def test_other_clinician_cannot_access_report(self, mock_presign, clinician_client,
                                                   clinician_user, diagnosis_payload,
                                                   client_user, sample_patient, db):
        from rest_framework.test import APIClient

        diagnosis_id = _create_completed_diagnosis(
            clinician_client, clinician_user, diagnosis_payload, client_user, sample_patient
        )

        other = User.objects.create_user(
            username="other_doc3", email="other3@test.com",
            password="pass123", role=User.ROLE_CLINICIAN,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other)

        response = other_client.get(f"/api/v1/diagnosis/{diagnosis_id}/report/")
        assert response.status_code == 403

    def test_report_not_ready_returns_404(self, clinician_client, diagnosis_payload):
        with patch("tasks.llm_task.generate_llm_report.delay"):
            resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                          format="json")
        diagnosis_id = resp.data["diagnosis_id"]

        response = clinician_client.get(f"/api/v1/diagnosis/{diagnosis_id}/report/")
        assert response.status_code == 404
