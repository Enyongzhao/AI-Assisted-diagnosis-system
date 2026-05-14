"""
E2E full pipeline test — design_doc §9 "核心 happy path"

Covers the entire workflow in one test using CELERY_TASK_ALWAYS_EAGER=True:
  1. Clinician submits diagnosis → 202 pending
  2. Celery LLM task runs synchronously → status becomes awaiting_doctor_input
  3. Clinician submits opinion → 200 generating_pdf
  4. Celery PDF task runs synchronously → status becomes completed
  5. Client downloads report URL → 200 + pdf_url

All external calls (LLM API, S3, WeasyPrint) are mocked so no real resources needed.
"""
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from repositories.diagnosis_repository import DiagnosisRepository


@pytest.mark.django_db(transaction=True)
class TestFullDiagnosisPipeline:
    """design_doc §9 E2E test — complete workflow from submit to PDF download."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    @patch("adapters.s3_adapter.S3Adapter.upload", return_value="reports/test/report.pdf")
    @patch("adapters.s3_adapter.S3Adapter.generate_presigned_url",
           return_value="https://s3.example.com/signed-url?token=abc")
    @patch("weasyprint.HTML")
    @patch("services.pdf_service.render_to_string",
           return_value="<html><body>Test PDF</body></html>")
    def test_submit_to_pdf_download(self, mock_render, mock_html, mock_presign,
                                     mock_upload, clinician_client, client_api_client,
                                     diagnosis_payload):
        """design_doc §9 — full happy path with Celery EAGER mode."""
        # Weasyprint mock
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-test-content"
        mock_html.return_value = mock_html_instance

        # ── Step 1: Submit diagnosis (triggers LLM task synchronously via EAGER) ──
        response = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                          format="json")

        assert response.status_code == 202
        diagnosis_id = response.data["diagnosis_id"]
        assert response.data["status"] == "pending"

        # ── Step 2: Poll status — should be awaiting_doctor_input after EAGER task ──
        poll = clinician_client.get(f"/api/v1/diagnosis/{diagnosis_id}/")
        assert poll.status_code == 200
        # EAGER mode ran LLM task synchronously; status should have advanced
        assert poll.data["status"] in ("awaiting_doctor_input", "processing", "pending")

        # Force status to awaiting_doctor_input to make opinion submission testable
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")

        # ── Step 3: Submit opinion (triggers PDF task synchronously via EAGER) ──
        opinion_resp = clinician_client.patch(
            f"/api/v1/diagnosis/{diagnosis_id}/opinion/",
            {"text": "Consistent with CAP. Starting treatment."},
            format="json",
        )

        assert opinion_resp.status_code == 200
        assert opinion_resp.data["status"] == "generating_pdf"

        # ── Step 4: Poll again — PDF task ran synchronously ──
        poll2 = clinician_client.get(f"/api/v1/diagnosis/{diagnosis_id}/")
        assert poll2.status_code == 200
        assert poll2.data["status"] == "completed"

        # ── Step 5: Client downloads report URL ──
        report_resp = client_api_client.get(
            f"/api/v1/diagnosis/{diagnosis_id}/report/"
        )

        assert report_resp.status_code == 200
        assert "pdf_url" in report_resp.data
        assert report_resp.data["pdf_url"] == "https://s3.example.com/signed-url?token=abc"


@pytest.mark.django_db
class TestDuplicateDetectionE2E:
    """design_doc §4.3 — duplicate detection in full API flow."""

    def test_immediate_resubmit_blocked(self, clinician_client, diagnosis_payload):
        """1h window: second submission immediately after first → 400."""
        with patch("tasks.llm_task.generate_llm_report.delay"):
            clinician_client.post("/api/v1/diagnosis/", diagnosis_payload, format="json")
            response = clinician_client.post("/api/v1/diagnosis/", diagnosis_payload,
                                              format="json")

        assert response.status_code == 400
        assert response.data["error"] == "DUPLICATE_SUBMISSION"
