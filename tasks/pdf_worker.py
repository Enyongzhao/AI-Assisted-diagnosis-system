"""
Lambda entry handler for PDF report generation — design_doc §6 / §7.2.

Production path:  SQS (pdf_queue) → Lambda (this handler) → core logic
Local dev path:   Celery task (tasks/pdf_task.py) — no SQS involved.
"""
import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django  # noqa: E402
django.setup()

from adapters.s3_adapter import S3Adapter  # noqa: E402
from repositories.diagnosis_repository import DiagnosisRepository  # noqa: E402
from repositories.doctor_opinion_repository import DoctorOpinionRepository  # noqa: E402
from repositories.llm_report_repository import LLMReportRepository  # noqa: E402
from repositories.report_repository import ReportRepository  # noqa: E402
from services.pdf_service import PDFService  # noqa: E402


def handler(event, context):
    """
    AWS Lambda entry point.

    SQS event structure (batch size = 1):
      {"Records": [{"body": "{\"diagnosis_id\": \"<uuid>\"}"}]}
    """
    results = []

    for record in event.get("Records", []):
        body = json.loads(record["body"])
        diagnosis_id = body["diagnosis_id"]
        _process(diagnosis_id)
        results.append({"diagnosis_id": diagnosis_id, "status": "ok"})

    return {"processed": results}


def _process(diagnosis_id: str):
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
