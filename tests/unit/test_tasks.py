"""
Unit tests for Celery tasks — design_doc §6 error / edge paths.

Tests:
  - LLM task returns early when job not found (line 67)
  - LLM task marks job 'failed' on exception (lines 102-105)
  - PDF task marks job 'failed' on exception (lines 77-80)
"""
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings


@pytest.mark.django_db
class TestLLMTaskEdgePaths:
    """design_doc §6 — generate_llm_report error paths."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    @patch("tasks.llm_task.DiagnosisRepository.update_status")
    @patch("tasks.llm_task.DiagnosisRepository.get_by_id", return_value=None)
    def test_returns_early_when_job_not_found(self, mock_get, mock_update_status):
        """If get_by_id returns None, task exits without calling update_status."""
        from tasks.llm_task import generate_llm_report

        generate_llm_report.apply(args=["nonexistent-id"])

        mock_update_status.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    @patch("tasks.llm_task.LLMAdapter.generate", side_effect=RuntimeError("LLM API down"))
    @patch("tasks.llm_task.PromptBuilder.build", return_value="prompt text")
    @patch("tasks.llm_task.DiagnosisRepository.update_status")
    @patch("tasks.llm_task.DiagnosisRepository.get_by_id")
    def test_marks_job_failed_on_exception(self, mock_get, mock_update, mock_build, mock_llm):
        """Exception inside try block → status set to 'failed' + retry raised."""
        mock_job = MagicMock()
        mock_job.age = 39
        mock_job.gender = "male"
        mock_job.temperature = None
        mock_job.blood_pressure = None
        mock_job.heart_rate = None
        mock_job.symptoms = []
        mock_job.duration_days = None
        mock_job.existing_conditions = []
        mock_job.free_text = None
        mock_get.return_value = mock_job

        from tasks.llm_task import generate_llm_report

        generate_llm_report.apply(args=["test-id"])

        failed_calls = [c for c in mock_update.call_args_list if "failed" in c[0]]
        assert len(failed_calls) > 0


@pytest.mark.django_db
class TestPDFTaskEdgePaths:
    """design_doc §6 — generate_pdf_report error paths."""

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    @patch("tasks.pdf_task.PDFService.render", side_effect=RuntimeError("WeasyPrint error"))
    @patch("tasks.pdf_task.DoctorOpinionRepository.get_by_diagnosis")
    @patch("tasks.pdf_task.LLMReportRepository.get_by_diagnosis")
    @patch("tasks.pdf_task.DiagnosisRepository.get_by_id")
    @patch("tasks.pdf_task.DiagnosisRepository.update_status")
    def test_marks_job_failed_on_exception(self, mock_update, mock_get_job,
                                            mock_get_report, mock_get_opinion,
                                            mock_render):
        """Exception in PDF render → status set to 'failed' + retry raised."""
        mock_get_job.return_value = MagicMock()
        mock_get_report.return_value = MagicMock()
        mock_get_opinion.return_value = MagicMock()

        from tasks.pdf_task import generate_pdf_report

        generate_pdf_report.apply(args=["test-id"])

        failed_calls = [c for c in mock_update.call_args_list if "failed" in c[0]]
        assert len(failed_calls) > 0
