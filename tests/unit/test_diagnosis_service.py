"""
Unit tests for DiagnosisService — design_doc §9.2 "重复提交检测三场景"

Three scenarios per design_doc §4.3:
  1. Hard Error  — submitted within DUPLICATE_HARD_ERROR_HOURS (default 1h)
  2. Soft Warning — submitted > hard_error_hours ago but within DUPLICATE_SOFT_WARN_HOURS
  3. Clean path   — no previous job found → proceed normally
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.diagnosis.exceptions import DuplicateSubmissionError
from services.diagnosis_service import DiagnosisService


def _make_recent_job(minutes_ago: float):
    job = MagicMock()
    job.id = "mock-uuid"
    job.submitted_at = timezone.now() - timedelta(minutes=minutes_ago)
    return job


@pytest.mark.django_db
class TestDiagnosisServiceDuplicateDetection:
    """design_doc §4.3 — duplicate detection business rules."""

    @override_settings(DUPLICATE_HARD_ERROR_HOURS=1.0, DUPLICATE_SOFT_WARN_HOURS=24.0)
    @patch("services.diagnosis_service.DiagnosisRepository.find_recent_by_patient")
    @patch("services.diagnosis_service.DiagnosisRepository.create")
    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_hard_error_within_1h(self, mock_delay, mock_create, mock_find,
                                   clinician_user, sample_patient):
        """Submitting within HARD_ERROR window → DuplicateSubmissionError (HTTP 400)."""
        mock_find.return_value = _make_recent_job(minutes_ago=30)

        with pytest.raises(DuplicateSubmissionError) as exc_info:
            DiagnosisService.submit(
                patient=sample_patient,
                submitted_by=clinician_user,
                structured_data={"age": 39, "gender": "male", "symptoms": []},
            )

        assert exc_info.value.original_diagnosis_id == "mock-uuid"
        mock_create.assert_not_called()
        mock_delay.assert_not_called()

    @override_settings(DUPLICATE_HARD_ERROR_HOURS=1.0, DUPLICATE_SOFT_WARN_HOURS=24.0)
    @patch("services.diagnosis_service.DiagnosisRepository.find_recent_by_patient")
    @patch("services.diagnosis_service.DiagnosisRepository.create")
    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_soft_warning_between_1h_and_24h(self, mock_delay, mock_create, mock_find,
                                              clinician_user, sample_patient):
        """Submitting between 1h–24h ago → 202 with POSSIBLE_DUPLICATE warning."""
        prev_job = _make_recent_job(minutes_ago=90)
        mock_find.return_value = prev_job
        mock_create.return_value = MagicMock(id="new-uuid")

        result = DiagnosisService.submit(
            patient=sample_patient,
            submitted_by=clinician_user,
            structured_data={"age": 39, "gender": "male", "symptoms": []},
        )

        assert result["has_warning"] is True
        assert result["warning_type"] == "POSSIBLE_DUPLICATE"
        assert result["previous_diagnosis_id"] == prev_job.id
        mock_create.assert_called_once()
        mock_delay.assert_called_once()

    @override_settings(DUPLICATE_HARD_ERROR_HOURS=1.0, DUPLICATE_SOFT_WARN_HOURS=24.0)
    @patch("services.diagnosis_service.DiagnosisRepository.find_recent_by_patient")
    @patch("services.diagnosis_service.DiagnosisRepository.create")
    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_no_warning_when_no_previous_job(self, mock_delay, mock_create, mock_find,
                                              clinician_user, sample_patient):
        """No previous job within soft-warn window → clean 202, no warning."""
        mock_find.return_value = None
        mock_create.return_value = MagicMock(id="new-uuid")

        result = DiagnosisService.submit(
            patient=sample_patient,
            submitted_by=clinician_user,
            structured_data={"age": 39, "gender": "male", "symptoms": []},
        )

        assert result["has_warning"] is False
        assert result["warning_type"] == ""
        assert result["previous_diagnosis_id"] is None
        mock_create.assert_called_once()
        mock_delay.assert_called_once()

    @override_settings(DUPLICATE_HARD_ERROR_HOURS=0.01, DUPLICATE_SOFT_WARN_HOURS=0.02)
    @patch("services.diagnosis_service.DiagnosisRepository.find_recent_by_patient")
    @patch("services.diagnosis_service.DiagnosisRepository.create")
    @patch("tasks.llm_task.generate_llm_report.delay")
    def test_configurable_time_windows(self, mock_delay, mock_create, mock_find,
                                        clinician_user, sample_patient):
        """Time windows are read from settings, not hardcoded."""
        # 1.1 minutes ago — beyond HARD (0.01h≈36s) but within SOFT (0.02h≈72s)
        mock_find.return_value = _make_recent_job(minutes_ago=1.1)
        mock_create.return_value = MagicMock(id="new-uuid")

        result = DiagnosisService.submit(
            patient=sample_patient,
            submitted_by=clinician_user,
            structured_data={"age": 39, "gender": "male", "symptoms": []},
        )

        assert result["has_warning"] is True
