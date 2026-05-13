"""
design_doc §5.1 — job_errors table
Written by the DLQ handler Lambda when a task exhausts retries.
1:N with DiagnosisJob (a job can have multiple retry failure records).
"""
from django.db import models

from apps.diagnosis.models.diagnosis_job import DiagnosisJob


class JobError(models.Model):
    diagnosis = models.ForeignKey(
        DiagnosisJob, on_delete=models.CASCADE, related_name="errors"
    )
    error_type = models.CharField(max_length=100)
    error_message = models.TextField()

    # design_doc §5.1 — SQS message ID for tracing DLQ failures
    sqs_message_id = models.CharField(max_length=256, blank=True, null=True)
    retry_count = models.IntegerField(default=0)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_errors"

    def __str__(self):
        return f"JobError [{self.error_type}] for {self.diagnosis_id}"
