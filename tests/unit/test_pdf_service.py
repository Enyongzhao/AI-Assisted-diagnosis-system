"""
Unit tests for PDFService — design_doc §9.2 "mock boto3"

Tests:
  - render() returns non-empty bytes
  - S3Adapter.upload() is called once by pdf_task
  - upload result has correct prefix
"""
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings


def _make_mock_job():
    job = MagicMock()
    job.id = "test-uuid-1234"
    job.age = 39
    job.gender = "male"
    job.temperature = 38.5
    job.blood_pressure = "130/85"
    job.heart_rate = 92
    job.symptoms = ["cough"]
    job.duration_days = 5
    job.existing_conditions = ["hypertension"]
    job.free_text = "Test free text"
    job.submitted_at = "2025-05-10T08:30:00Z"
    job.patient = MagicMock()
    job.patient.name = "John Smith"
    job.patient.date_of_birth = "1985-03-22"
    job.patient.gender = "male"
    return job


def _make_mock_report():
    report = MagicMock()
    report.summary = "Test summary"
    report.differential_diagnosis = ["Diagnosis A", "Diagnosis B"]
    report.recommended_investigations = ["X-ray", "Blood test"]
    report.risk_factors = ["Hypertension"]
    report.llm_provider = "mock"
    report.llm_model = "mock-llm"
    report.generated_at = "2025-05-10T08:30:08Z"
    return report


def _make_mock_opinion():
    opinion = MagicMock()
    opinion.text = "Consistent with CAP. Initiating antibiotics."
    opinion.submitted_by = MagicMock()
    opinion.submitted_by.username = "dr_smith"
    opinion.submitted_at = "2025-05-10T09:15:00Z"
    return opinion


class TestPDFService:
    """design_doc §2 — WeasyPrint HTML→PDF generation."""

    @patch("weasyprint.HTML")
    @patch("services.pdf_service.render_to_string")
    def test_render_returns_bytes(self, mock_render, mock_html):
        """render() should return non-empty bytes (PDF binary content)."""
        from services.pdf_service import PDFService

        mock_render.return_value = "<html><body>Test</body></html>"
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-test-content"
        mock_html.return_value = mock_html_instance

        result = PDFService.render(_make_mock_job(), _make_mock_report(), _make_mock_opinion())

        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("weasyprint.HTML")
    @patch("services.pdf_service.render_to_string")
    def test_render_uses_correct_template(self, mock_render, mock_html):
        """design_doc §6 — template path is pdf/report.html."""
        from services.pdf_service import PDFService

        mock_render.return_value = "<html/>"
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF-1"
        mock_html.return_value = mock_html_instance

        PDFService.render(_make_mock_job(), _make_mock_report(), _make_mock_opinion())

        args = mock_render.call_args
        assert args[0][0] == "pdf/report.html"

    @patch("pathlib.Path.write_bytes")
    @patch("pathlib.Path.mkdir")
    def test_s3_upload_uses_local_filesystem_fallback(self, mock_mkdir, mock_write):
        """Test settings have no S3 bucket → upload writes to local media/ and returns s3_key."""
        from adapters.s3_adapter import S3Adapter

        s3_key = S3Adapter.upload(b"%PDF-1", "reports/test-uuid/report.pdf")

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write.assert_called_once_with(b"%PDF-1")
        assert s3_key == "reports/test-uuid/report.pdf"

    @override_settings(
        AWS_S3_BUCKET_NAME="test-bucket",
        AWS_DEFAULT_REGION="us-east-1",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )
    @patch("boto3.client")
    def test_s3_upload_with_bucket_calls_put_object(self, mock_boto_client):
        """When AWS_S3_BUCKET_NAME is set → boto3.put_object called with correct content type."""
        from adapters.s3_adapter import S3Adapter

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.put_object.return_value = {}

        s3_key = S3Adapter.upload(b"%PDF-1", "reports/test-uuid/report.pdf")

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/pdf"
        assert call_kwargs["Bucket"] == "test-bucket"
        assert s3_key == "reports/test-uuid/report.pdf"

    @override_settings(
        AWS_S3_BUCKET_NAME="test-bucket",
        AWS_DEFAULT_REGION="us-east-1",
        AWS_ACCESS_KEY_ID="test-key",
        AWS_SECRET_ACCESS_KEY="test-secret",
    )
    @patch("boto3.client")
    def test_s3_presigned_url_with_bucket(self, mock_boto_client):
        """When AWS_S3_BUCKET_NAME is set → boto3.generate_presigned_url called."""
        from adapters.s3_adapter import S3Adapter

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/signed?token=x"

        url = S3Adapter.generate_presigned_url("reports/test-uuid/report.pdf")

        mock_s3.generate_presigned_url.assert_called_once()
        assert url == "https://s3.example.com/signed?token=x"
