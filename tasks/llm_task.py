"""
LLM Celery task — design_doc §6

generate_llm_report:
  pending → processing → awaiting_doctor_input  (happy path)
  processing → failed                            (on any exception, after max_retries)

Retry policy: max 3 attempts, 30-second delay between retries.
"""
from celery import shared_task

from adapters.llm_adapter import LLMAdapter
from repositories.diagnosis_repository import DiagnosisRepository
from repositories.llm_report_repository import LLMReportRepository
from services.prompt_builder import PromptBuilder


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_llm_report(self, diagnosis_id: str):
    """
    design_doc §6 — triggered by POST /api/v1/diagnosis/.

    1. Mark job 'processing'
    2. Reconstruct structured dict from flat DiagnosisJob columns
    3. Build prompt via PromptBuilder
    4. Call LLM via LLMAdapter (routes to Claude / OpenAI / Mock)
    5. Persist result to llm_reports
    6. Advance status to 'awaiting_doctor_input'
    """
    try:
        job = DiagnosisRepository.get_by_id(diagnosis_id)
        if job is None:
            # Job deleted between submission and execution — nothing to do.
            return

        DiagnosisRepository.update_status(diagnosis_id, "processing")

        structured = {
            "age": job.age,
            "gender": job.gender,
            "temperature": float(job.temperature) if job.temperature is not None else None,
            "blood_pressure": job.blood_pressure,
            "heart_rate": job.heart_rate,
            "symptoms": job.symptoms,
            "duration_days": job.duration_days,
            "existing_conditions": job.existing_conditions,
        }

        prompt = PromptBuilder.build(structured, job.free_text)
        report_data = LLMAdapter.generate(prompt)

        LLMReportRepository.create(diagnosis_id=job.id, report_data=report_data)
        DiagnosisRepository.update_status(diagnosis_id, "awaiting_doctor_input")

    except Exception as exc:
        DiagnosisRepository.update_status(diagnosis_id, "failed")
        raise self.retry(exc=exc)
