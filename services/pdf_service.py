"""
PDF Service — design_doc §2 "PDF report generation: WeasyPrint HTML → PDF"

Renders the diagnosis report HTML template and converts it to PDF bytes.
The PDF is then uploaded by the caller (tasks/pdf_task.py) via S3Adapter.
"""
from django.template.loader import render_to_string


class PDFService:

    @staticmethod
    def render(job, report, opinion) -> bytes:
        """
        design_doc §6 — render templates/pdf/report.html → PDF bytes.

        job:     DiagnosisJob instance
        report:  LLMReport instance
        opinion: DoctorOpinion instance
        """
        from weasyprint import HTML

        html_string = render_to_string(
            "pdf/report.html",
            {"job": job, "report": report, "opinion": opinion},
        )
        return HTML(string=html_string).write_pdf()
