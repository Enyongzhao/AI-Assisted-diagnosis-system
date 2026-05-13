"""
design_doc §5.1 — doctor_opinions table
1:1 with DiagnosisJob. Created via PATCH /api/v1/diagnosis/{id}/opinion/ (Phase 2).
"""
from django.db import models

from apps.authentication.models import User
from apps.diagnosis.models.diagnosis_job import DiagnosisJob


class DoctorOpinion(models.Model):
    diagnosis = models.OneToOneField(
        DiagnosisJob, on_delete=models.CASCADE, related_name="doctor_opinion"
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="submitted_opinions"
    )
    # design_doc §2 — "Clinician fills in free-text diagnosis opinion"
    text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "doctor_opinions"

    def __str__(self):
        return f"DoctorOpinion for {self.diagnosis_id} by {self.submitted_by}"
