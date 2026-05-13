"""
Opinion Service — design_doc §4.3 PATCH /api/v1/diagnosis/{id}/opinion/

Validates status, saves the doctor's opinion, triggers PDF generation task.
"""
from apps.diagnosis.exceptions import DiagnosisStatusError
from apps.diagnosis.models import DiagnosisJob
from repositories.diagnosis_repository import DiagnosisRepository
from repositories.doctor_opinion_repository import DoctorOpinionRepository


class OpinionService:

    @staticmethod
    def submit(diagnosis_id, text: str, submitted_by):
        """
        design_doc §4.3 — clinician submits diagnosis opinion.

        Validates that status == awaiting_doctor_input, then:
          1. Creates DoctorOpinion record
          2. Fires generate_pdf_report.delay()
        Returns the new DoctorOpinion instance.
        """
        job = DiagnosisRepository.get_by_id(diagnosis_id)
        if job is None:
            raise ValueError("Diagnosis not found.")

        if job.status != DiagnosisJob.STATUS_AWAITING_DOCTOR:
            raise DiagnosisStatusError(
                f"Cannot submit opinion: job status is '{job.status}', "
                f"expected '{DiagnosisJob.STATUS_AWAITING_DOCTOR}'."
            )

        opinion = DoctorOpinionRepository.create(
            diagnosis_id=diagnosis_id,
            text=text,
            submitted_by=submitted_by,
        )

        # design_doc §6 — fire PDF generation asynchronously
        from tasks.pdf_task import generate_pdf_report
        generate_pdf_report.delay(str(diagnosis_id))

        return opinion
