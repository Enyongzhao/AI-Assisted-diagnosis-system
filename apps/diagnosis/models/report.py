"""
design_doc §5.1 — reports table
Stores the S3 key after WeasyPrint PDF generation (Phase 2).
Pre-signed URL is generated on demand in the /report/ endpoint.
"""
from django.db import models

from apps.diagnosis.models.diagnosis_job import DiagnosisJob


class Report(models.Model):
    diagnosis = models.OneToOneField(
        DiagnosisJob, on_delete=models.CASCADE, related_name="report"
    )
    # design_doc §5.1 — S3 object key, e.g. "reports/{diagnosis_id}/report.pdf"
    s3_key = models.CharField(max_length=512)
    file_size_bytes = models.IntegerField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reports"

    def __str__(self):
        return f"Report for {self.diagnosis_id} → {self.s3_key}"
