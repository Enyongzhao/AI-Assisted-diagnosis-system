"""
Repository layer for Patient — design_doc §12 "Controller → Service → Repository"
All Patient DB access goes through here; views never call Patient.objects directly.
Phase 1: basic CRUD. Phase 4 will add duplicate-detection helpers.
"""
from apps.patients.models import Patient


class PatientRepository:

    @staticmethod
    def create(*, name, date_of_birth, gender, created_by, contact_email=None, linked_user=None):
        return Patient.objects.create(
            name=name,
            date_of_birth=date_of_birth,
            gender=gender,
            contact_email=contact_email,
            created_by=created_by,
            linked_user=linked_user,
        )

    @staticmethod
    def get_by_id(patient_id):
        """Returns Patient or None; excludes soft-deleted records."""
        try:
            return Patient.objects.get(id=patient_id, is_deleted=False)
        except Patient.DoesNotExist:
            return None

    @staticmethod
    def list_active():
        """All non-deleted patients, newest first."""
        return Patient.objects.filter(is_deleted=False).order_by("-created_at")

    @staticmethod
    def update(patient, **fields):
        for key, value in fields.items():
            setattr(patient, key, value)
        patient.save(update_fields=list(fields.keys()) + ["updated_at"])
        return patient

    @staticmethod
    def soft_delete(patient):
        """design_doc §4.2 — DELETE is soft-delete (Admin only)."""
        patient.is_deleted = True
        patient.save(update_fields=["is_deleted", "updated_at"])
