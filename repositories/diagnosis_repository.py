"""
Repository layer for DiagnosisJob — design_doc §12 "Controller → Service → Repository"
Phase 1: create + get + role-based list queries + update_status.
Phase 2: add find_recent_by_patient() for duplicate detection (used by DiagnosisService).
"""
from django.utils import timezone

from apps.diagnosis.models import DiagnosisJob


class DiagnosisRepository:

    @staticmethod
    def create(*, patient, submitted_by, structured_data, free_text=""):
        """
        Flatten the structured_data dict into DiagnosisJob columns.
        design_doc §4.3 — structured_data fields map 1:1 to table columns.
        """
        return DiagnosisJob.objects.create(
            patient=patient,
            submitted_by=submitted_by,
            age=structured_data.get("age"),
            gender=structured_data.get("gender", ""),
            temperature=structured_data.get("temperature"),
            blood_pressure=structured_data.get("blood_pressure", ""),
            heart_rate=structured_data.get("heart_rate"),
            symptoms=structured_data.get("symptoms", []),
            duration_days=structured_data.get("duration_days"),
            existing_conditions=structured_data.get("existing_conditions", []),
            free_text=free_text,
        )

    @staticmethod
    def get_by_id(diagnosis_id):
        """Returns DiagnosisJob or None; excludes soft-deleted records."""
        try:
            return DiagnosisJob.objects.select_related(
                "patient", "submitted_by"
            ).get(id=diagnosis_id, is_deleted=False)
        except (DiagnosisJob.DoesNotExist, ValueError):
            return None

    # ── Role-based list queries — design_doc §4.3 GET /api/v1/diagnosis/ ──

    @staticmethod
    def list_for_clinician(user):
        """Clinician sees only jobs they submitted."""
        return (
            DiagnosisJob.objects
            .filter(submitted_by=user, is_deleted=False)
            .select_related("patient")
            .order_by("-submitted_at")
        )

    @staticmethod
    def list_for_client(user):
        """Client sees only jobs for the patient linked to their account."""
        return (
            DiagnosisJob.objects
            .filter(patient__linked_user=user, is_deleted=False)
            .select_related("patient")
            .order_by("-submitted_at")
        )

    @staticmethod
    def list_all():
        """Admin sees every non-deleted job."""
        return (
            DiagnosisJob.objects
            .filter(is_deleted=False)
            .select_related("patient", "submitted_by")
            .order_by("-submitted_at")
        )

    @staticmethod
    def update_status(diagnosis_id, new_status):
        """
        Called by Celery tasks to advance the status machine.
        Also stamps completed_at when the job reaches the terminal 'completed' state.
        """
        update_fields = {"status": new_status}
        if new_status == DiagnosisJob.STATUS_COMPLETED:
            update_fields["completed_at"] = timezone.now()
        DiagnosisJob.objects.filter(id=diagnosis_id).update(**update_fields)

    @staticmethod
    def find_recent_by_patient(patient_id, within_hours: int = 24):
        """
        design_doc §4.3 — duplicate detection.
        Returns the most recent non-deleted DiagnosisJob for the given patient
        submitted within the last `within_hours` hours, or None.
        Phase 4 DiagnosisService uses this to decide Hard Error vs Soft Warning.
        """
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(hours=within_hours)
        return (
            DiagnosisJob.objects
            .filter(patient_id=patient_id, submitted_at__gte=cutoff, is_deleted=False)
            .order_by("-submitted_at")
            .first()
        )
