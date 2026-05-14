"""
Lambda entry handler for LLM report generation — design_doc §6 / §7.2.

Production path:  SQS (llm_queue) → Lambda (this handler) → core logic
Local dev path:   Celery task (tasks/llm_task.py) — no SQS involved.

The handler bootstraps Django once per cold start, then delegates to the
same generate_llm_report logic used by the Celery task, keeping both
environments on identical business logic.
"""
import json
import os

# Bootstrap Django before importing any app code.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django  # noqa: E402
django.setup()

from adapters.llm_adapter import LLMAdapter  # noqa: E402
from repositories.diagnosis_repository import DiagnosisRepository  # noqa: E402
from repositories.llm_report_repository import LLMReportRepository  # noqa: E402
from services.prompt_builder import PromptBuilder  # noqa: E402


def handler(event, context):
    """
    AWS Lambda entry point.

    SQS event structure (batch size = 1 configured in Terraform):
      {"Records": [{"body": "{\"diagnosis_id\": \"<uuid>\"}"}]}

    Returns a dict so Lambda logs the result; unhandled exceptions
    are re-raised so the message goes to the DLQ after max retries.
    """
    results = []

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        diagnosis_id = body["diagnosis_id"]
        _process(diagnosis_id)
        results.append({"diagnosis_id": diagnosis_id, "status": "ok"})

    return {"processed": results}


def _process(diagnosis_id: str):
    job = DiagnosisRepository.get_by_id(diagnosis_id)
    if job is None:
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
