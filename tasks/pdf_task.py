"""
PDF Celery task — design_doc §6

generate_pdf_report:
  awaiting_doctor_input → generating_pdf → completed  (happy path)
  generating_pdf → failed                              (on any exception, after max_retries)

Retry policy: max 3 attempts, 10-second delay between retries.
"""
from celery import shared_task

from adapters.s3_adapter import S3Adapter
from repositories.diagnosis_repository import DiagnosisRepository
from repositories.doctor_opinion_repository import DoctorOpinionRepository
from repositories.llm_report_repository import LLMReportRepository
from repositories.report_repository import ReportRepository
from services.pdf_service import PDFService


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_pdf_report(self, diagnosis_id: str):
    """
    design_doc §6 — triggered by PATCH /api/v1/diagnosis/{id}/opinion/.

    1. Mark job 'generating_pdf'
    2. Fetch job, LLM report, doctor opinion from DB
    3. Render HTML template → PDF bytes via WeasyPrint
    4. Upload to S3 (or local filesystem in dev)
    5. Create Report record (stores s3_key + file size)
    6. Advance status to 'completed'
    """
    try:
        DiagnosisRepository.update_status(diagnosis_id, "generating_pdf")

        job = DiagnosisRepository.get_by_id(diagnosis_id)
        report = LLMReportRepository.get_by_diagnosis(diagnosis_id)
        opinion = DoctorOpinionRepository.get_by_diagnosis(diagnosis_id)

        pdf_bytes = PDFService.render(job, report, opinion)

        s3_key = S3Adapter.upload(
            pdf_bytes,
            f"reports/{diagnosis_id}/report.pdf",
        )

        ReportRepository.create(
            diagnosis_id=diagnosis_id,
            s3_key=s3_key,
            file_size_bytes=len(pdf_bytes),
        )
        DiagnosisRepository.update_status(diagnosis_id, "completed")

    except Exception as exc:
        DiagnosisRepository.update_status(diagnosis_id, "failed")
        raise self.retry(exc=exc)
