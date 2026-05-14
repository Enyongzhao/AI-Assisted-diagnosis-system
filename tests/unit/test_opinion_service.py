"""
Unit tests for OpinionService — design_doc §9.2

Tests:
  - Status must be awaiting_doctor_input, otherwise DiagnosisStatusError
  - Valid submission creates DoctorOpinion and fires pdf task
"""
from unittest.mock import MagicMock, patch

import pytest

from apps.diagnosis.exceptions import DiagnosisStatusError
from apps.diagnosis.models.diagnosis_job import DiagnosisJob


def _make_job(status):
    job = MagicMock()
    job.id = "test-uuid"
    job.status = status
    return job


class TestOpinionService:
    """design_doc §4.3 PATCH /opinion/ — status validation."""

    @patch("services.opinion_service.DiagnosisRepository.get_by_id")
    @patch("services.opinion_service.DoctorOpinionRepository.create")
    @patch("tasks.pdf_task.generate_pdf_report.delay")
    def test_valid_opinion_submission(self, mock_delay, mock_create, mock_get,
                                       clinician_user):
        """Happy path: awaiting_doctor_input → creates opinion + fires PDF task."""
        from services.opinion_service import OpinionService

        mock_get.return_value = _make_job(DiagnosisJob.STATUS_AWAITING_DOCTOR)
        mock_opinion = MagicMock()
        mock_create.return_value = mock_opinion

        result = OpinionService.submit(
            diagnosis_id="test-uuid",
            text="Patient has pneumonia.",
            submitted_by=clinician_user,
        )

        assert result == mock_opinion
        mock_create.assert_called_once()
        mock_delay.assert_called_once_with("test-uuid")

    @patch("services.opinion_service.DiagnosisRepository.get_by_id")
    def test_raises_if_status_not_awaiting(self, mock_get, clinician_user):
        """design_doc §4.3 — wrong status → DiagnosisStatusError."""
        from services.opinion_service import OpinionService

        for bad_status in [
            DiagnosisJob.STATUS_PENDING,
            DiagnosisJob.STATUS_PROCESSING,
            DiagnosisJob.STATUS_COMPLETED,
            DiagnosisJob.STATUS_FAILED,
        ]:
            mock_get.return_value = _make_job(bad_status)

            with pytest.raises(DiagnosisStatusError):
                OpinionService.submit(
                    diagnosis_id="test-uuid",
                    text="Some opinion.",
                    submitted_by=clinician_user,
                )

    @patch("services.opinion_service.DiagnosisRepository.get_by_id")
    def test_raises_if_job_not_found(self, mock_get, clinician_user):
        """Non-existent diagnosis_id raises ValueError."""
        from services.opinion_service import OpinionService

        mock_get.return_value = None

        with pytest.raises(ValueError, match="not found"):
            OpinionService.submit(
                diagnosis_id="nonexistent-id",
                text="Some opinion.",
                submitted_by=clinician_user,
            )
