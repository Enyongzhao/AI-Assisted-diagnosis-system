"""
design_doc §5.1 — llm_reports table
1:1 with DiagnosisJob. Stores structured LLM output + raw JSONB response.
Created by the Celery/Lambda worker in Phase 2.
"""
from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.diagnosis.models.diagnosis_job import DiagnosisJob


class LLMReport(models.Model):
    PROVIDER_CLAUDE = "claude"
    PROVIDER_OPENAI = "openai"

    PROVIDER_CHOICES = [
        (PROVIDER_CLAUDE, "Claude"),
        (PROVIDER_OPENAI, "OpenAI"),
    ]

    # design_doc §5.1 — unique enforces 1:1 relationship
    diagnosis = models.OneToOneField(
        DiagnosisJob, on_delete=models.CASCADE, related_name="llm_report"
    )

    llm_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    llm_model = models.CharField(max_length=100)  # e.g. 'claude-sonnet-4-6'

    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()

    # design_doc §4.3 — structured fields parsed from LLM JSON response
    summary = models.TextField()
    differential_diagnosis = ArrayField(models.TextField())
    recommended_investigations = ArrayField(models.TextField())
    risk_factors = ArrayField(models.TextField())

    # design_doc §5.1 — raw JSONB backup of complete LLM response
    raw_response = models.JSONField()

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "llm_reports"

    def __str__(self):
        return f"LLMReport for {self.diagnosis_id} by {self.llm_provider}"
