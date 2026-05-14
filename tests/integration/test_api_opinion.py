"""
Integration tests for opinion API — design_doc §9.3 / §4.3

Tests:
  - Clinician can submit opinion when status=awaiting_doctor_input → 200
  - Non-submitter clinician cannot submit opinion → 403
  - Wrong status → 400 DiagnosisStatusError
"""
from unittest.mock import patch

import pytest

from apps.authentication.models import User
from apps.diagnosis.models import DiagnosisJob
from repositories.diagnosis_repository import DiagnosisRepository


def _submit_diagnosis(clinician_client, diagnosis_payload):
    """Helper: POST and return diagnosis_id."""
    with patch("tasks.llm_task.generate_llm_report.delay"):
        resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                      format="json")
    return resp.data["diagnosis_id"]


@pytest.mark.django_db
class TestOpinionSubmit:
    """design_doc §4.3 PATCH /api/v1/diagnosis/{id}/opinion/"""

    @patch("tasks.pdf_task.generate_pdf_report.delay")
    def test_clinician_can_submit_opinion_when_awaiting(self, mock_pdf_delay,
                                                         clinician_client, clinician_user,
                                                         diagnosis_payload):
        diagnosis_id = _submit_diagnosis(clinician_client, diagnosis_payload)

        # Force status to awaiting_doctor_input
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")

        response = clinician_client.patch(
            f"/api/v1/diagnosis/{diagnosis_id}/opinion/",
            {"text": "Patient has pneumonia. Prescribing amoxicillin."},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "generating_pdf"
        mock_pdf_delay.assert_called_once()

    def test_wrong_status_returns_400(self, clinician_client, diagnosis_payload):
        """design_doc §4.3 — DiagnosisStatusError → HTTP 400."""
        diagnosis_id = _submit_diagnosis(clinician_client, diagnosis_payload)
        # Status is 'pending', not 'awaiting_doctor_input'

        with patch("tasks.pdf_task.generate_pdf_report.delay"):
            response = clinician_client.patch(
                f"/api/v1/diagnosis/{diagnosis_id}/opinion/",
                {"text": "Some opinion."},
                format="json",
            )

        assert response.status_code == 400

    @patch("tasks.pdf_task.generate_pdf_report.delay")
    def test_other_clinician_cannot_submit_opinion(self, mock_pdf_delay,
                                                    clinician_client, diagnosis_payload,
                                                    db):
        """design_doc §4.3 — only the submitting clinician can write opinion."""
        from rest_framework.test import APIClient

        diagnosis_id = _submit_diagnosis(clinician_client, diagnosis_payload)
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")

        other = User.objects.create_user(
            username="other_doc2", email="other2@test.com",
            password="pass123", role=User.ROLE_CLINICIAN,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other)

        response = other_client.patch(
            f"/api/v1/diagnosis/{diagnosis_id}/opinion/",
            {"text": "Not my patient."},
            format="json",
        )

        assert response.status_code == 403

    def test_client_cannot_submit_opinion(self, client_api_client, clinician_client,
                                           diagnosis_payload):
        diagnosis_id = _submit_diagnosis(clinician_client, diagnosis_payload)
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")

        response = client_api_client.patch(
            f"/api/v1/diagnosis/{diagnosis_id}/opinion/",
            {"text": "I am not a doctor."},
            format="json",
        )

        assert response.status_code == 403
