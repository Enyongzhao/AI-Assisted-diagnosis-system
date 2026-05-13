"""
design_doc §5.1 — patients table
Soft-delete via is_deleted; linked_user connects a Patient to a Client account.
"""
from django.db import models

from apps.authentication.models import User


class Patient(models.Model):
    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_OTHER = "other"

    GENDER_CHOICES = [
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
    ]

    name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    contact_email = models.EmailField(blank=True, null=True)

    # design_doc §5.1 — optional link to a Client user account
    linked_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="patient_profile",
    )

    # Clinician who registered the patient
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_patients",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # design_doc §4.2 — DELETE is soft-delete (Admin only)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "patients"

    def __str__(self):
        return f"{self.name} (DOB: {self.date_of_birth})"
