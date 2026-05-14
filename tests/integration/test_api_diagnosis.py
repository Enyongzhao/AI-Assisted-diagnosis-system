"""
Integration tests for diagnosis API — design_doc §9.3 / §4.3

Tests:
  - POST returns 202 + diagnosis_id, fires LLM task
  - Client role cannot submit (403)
  - Duplicate within 1h returns 400 DUPLICATE_SUBMISSION
  - GET polling returns correct fields
  - Cross-patient access forbidden
"""
from unittest.mock import patch

import pytest


@pytest.mark.django_db
class TestDiagnosisSubmit:
    """design_doc §4.3 POST /api/v1/diagnosis/"""

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_clinician_submit_returns_202(self, mock_delay, clinician_client,
                                          diagnosis_payload):
        response = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                          format="json")

        assert response.status_code == 202
        assert "diagnosis_id" in response.data
        assert response.data["status"] == "pending"
        mock_delay.assert_called_once()

    def test_client_cannot_submit_diagnosis(self, client_api_client, diagnosis_payload):
        response = client_api_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                           format="json")
        assert response.status_code == 403

    def test_unauthenticated_cannot_submit(self, api_client, diagnosis_payload):
        response = api_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                    format="json")
        assert response.status_code == 401

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_duplicate_within_1h_returns_400(self, mock_delay, clinician_client,
                                              diagnosis_payload):
        """design_doc §4.3 — hard error path."""
        # First submission
        clinician_client.post("/api/v1/diagnosis/", diagnosis_payload, format="json")

        # Second submission immediately after (within 1h window)
        response = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                          format="json")

        assert response.status_code == 400
        assert response.data["error"] == "DUPLICATE_SUBMISSION"
        assert "original_diagnosis_id" in response.data

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_missing_patient_id_returns_400(self, mock_delay, clinician_client):
        response = clinician_client.post("/api/v1/diagnosis/", {
            "structured_data": {"age": 39},
        }, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestDiagnosisDetail:
    """design_doc §4.3 GET /api/v1/diagnosis/{id}/"""

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_clinician_can_poll_own_job(self, mock_delay, clinician_client,
                                        diagnosis_payload):
        submit_resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                             format="json")
        diagnosis_id = submit_resp.data["diagnosis_id"]

        response = clinician_client.get(f"/api/v1/diagnosis/{diagnosis_id}/")

        assert response.status_code == 200
        assert response.data["status"] in [
            "pending", "processing", "awaiting_doctor_input",
            "generating_pdf", "completed", "failed",
        ]

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_client_can_view_own_diagnosis(self, mock_delay, clinician_client,
                                            client_api_client, diagnosis_payload):
        """Client can view diagnosis for their linked patient."""
        submit_resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                             format="json")
        diagnosis_id = submit_resp.data["diagnosis_id"]

        response = client_api_client.get(f"/api/v1/diagnosis/{diagnosis_id}/")
        assert response.status_code == 200

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_other_clinician_cannot_view_job(self, mock_delay, clinician_client,
                                              diagnosis_payload, db):
        """design_doc §4.3 — access control: different clinician cannot view."""
        from apps.authentication.models import User
        from rest_framework.test import APIClient

        other = User.objects.create_user(
            username="other_doc", email="other@test.com",
            password="pass123", role=User.ROLE_CLINICIAN,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other)

        submit_resp = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                             format="json")
        diagnosis_id = submit_resp.data["diagnosis_id"]

        response = other_client.get(f"/api/v1/diagnosis/{diagnosis_id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestDiagnosisList:
    """design_doc §4.3 GET /api/v1/diagnosis/"""

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_clinician_sees_own_jobs(self, mock_delay, clinician_client,
                                     diagnosis_payload):
        clinician_client.post("/api/v1/diagnosis/", diagnosis_payload, format="json")
        response = clinician_client.get("/api/v1/diagnosis/")

        assert response.status_code == 200
        assert response.data["count"] >= 1

    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_admin_sees_all_jobs(self, mock_delay, clinician_client, admin_client,
                                  diagnosis_payload):
        clinician_client.post("/api/v1/diagnosis/", diagnosis_payload, format="json")
        response = admin_client.get("/api/v1/diagnosis/")

        assert response.status_code == 200
        assert response.data["count"] >= 1
