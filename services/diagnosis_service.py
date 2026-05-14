"""
DiagnosisService — design_doc §4.3 Phase 4: duplicate detection + job creation.

Business rules (design_doc §4.3):
  - 1h 内重复提交同一患者  → DuplicateSubmissionError (→ exception_handler → HTTP 400)
  - 超 1h、24h 内重复提交  → 正常创建，has_warning=True, warning_type="POSSIBLE_DUPLICATE"
  - 无历史记录             → 正常创建

Controller (view) calls DiagnosisService.submit() — never touches Repository directly.
"""
from datetime import timedelta

from django.utils import timezone

from django.conf import settings

from apps.diagnosis.exceptions import DuplicateSubmissionError
from repositories.diagnosis_repository import DiagnosisRepository


class DiagnosisService:
    """design_doc §4.3 — service layer for diagnosis submission."""

    @staticmethod
    def submit(*, patient, submitted_by, structured_data, free_text=""):
        """
        Create a new DiagnosisJob with duplicate detection.

        Time windows are read from settings so they can be overridden via .env
        for testing (e.g. DUPLICATE_HARD_ERROR_HOURS=0.01 ≈ 36 seconds).

        Returns a dict:
        {
            "job": DiagnosisJob,
            "has_warning": bool,
            "warning_type": str | None,          # "POSSIBLE_DUPLICATE" or None
            "warning_message": str | None,
            "previous_diagnosis_id": UUID | None,
        }

        Raises DuplicateSubmissionError when a job was submitted for the same patient
        within HARD_ERROR_HOURS — the DRF exception handler maps this to HTTP 400.
        """
        hard_error_hours = getattr(settings, "DUPLICATE_HARD_ERROR_HOURS", 1.0)
        soft_warn_hours  = getattr(settings, "DUPLICATE_SOFT_WARN_HOURS",  24.0)

        # Find the most recent job for this patient within the soft-warning window
        recent = DiagnosisRepository.find_recent_by_patient(
            patient_id=patient.id,
            within_hours=soft_warn_hours,
        )

        has_warning = False
        warning_type = ""
        warning_message = None
        previous_id = None

        if recent is not None:
            age = timezone.now() - recent.submitted_at

            if age <= timedelta(hours=hard_error_hours):
                # design_doc §4.3 — Hard Error path
                raise DuplicateSubmissionError(
                    message="A diagnosis for this patient was submitted within the last hour.",
                    original_diagnosis_id=recent.id,
                    original_submitted_at=recent.submitted_at,
                )

            # design_doc §4.3 — Soft Warning path (> 1h but ≤ 24h)
            has_warning = True
            warning_type = "POSSIBLE_DUPLICATE"
            warning_message = "A recent diagnosis exists for this patient. Proceeding."
            previous_id = recent.id

        # Create the job; pass warning metadata so it is persisted on the record
        job = DiagnosisRepository.create(
            patient=patient,
            submitted_by=submitted_by,
            structured_data=structured_data,
            free_text=free_text,
            has_warning=has_warning,
            warning_type=warning_type,
        )

        # design_doc §6 — fire async LLM task; the view returns 202 immediately
        from tasks.llm_task import generate_llm_report
        generate_llm_report.delay(str(job.id))

        return {
            "job": job,
            "has_warning": has_warning,
            "warning_type": warning_type,
            "warning_message": warning_message,
            "previous_diagnosis_id": previous_id,
        }
