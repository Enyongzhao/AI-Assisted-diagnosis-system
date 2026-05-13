"""
design_doc §5.1 — diagnosis_jobs table (core table)
UUID primary key; PostgreSQL TEXT[] for symptoms and existing_conditions;
6-state status machine; has_warning flag for soft duplicate detection.
"""
import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.authentication.models import User
from apps.patients.models import Patient


class DiagnosisJob(models.Model):
    # design_doc §5.1 status CHECK constraint values
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_AWAITING_DOCTOR = "awaiting_doctor_input"
    STATUS_GENERATING_PDF = "generating_pdf"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_AWAITING_DOCTOR, "Awaiting Doctor Input"),
        (STATUS_GENERATING_PDF, "Generating PDF"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    # design_doc §5.1 — UUID primary key (avoids ID enumeration attacks)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    patient = models.ForeignKey(
        Patient, on_delete=models.PROTECT, related_name="diagnosis_jobs"
    )
    submitted_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="submitted_diagnoses"
    )

    # design_doc §4.3 structured_data fields — mirrored flat in the table
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True, default="")
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    blood_pressure = models.CharField(max_length=20, blank=True, default="")
    heart_rate = models.IntegerField(null=True, blank=True)

    # PostgreSQL TEXT[] arrays — design_doc §5.1 "PostgreSQL array"
    symptoms = ArrayField(models.TextField(), default=list, blank=True)
    existing_conditions = ArrayField(models.TextField(), default=list, blank=True)

    duration_days = models.IntegerField(null=True, blank=True)

    # design_doc §4.3 — free-text clinical notes from clinician
    free_text = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING
    )

    # design_doc §4.3 — soft warning flag for possible duplicate submissions
    has_warning = models.BooleanField(default=False)
    warning_type = models.CharField(max_length=50, blank=True, default="")

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "diagnosis_jobs"
        # design_doc §5.1 — three indexes
        indexes = [
            models.Index(fields=["patient", "submitted_at"], name="idx_diagnosis_patient"),
            models.Index(fields=["status"], name="idx_diagnosis_status"),
            models.Index(fields=["submitted_by"], name="idx_diagnosis_submitter"),
        ]

    def __str__(self):
        return f"DiagnosisJob {self.id} — {self.patient} [{self.status}]"
