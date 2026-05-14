"""
Repository layer for DoctorOpinion — design_doc §5.1 doctor_opinions table.
Called by services/opinion_service.py after the Clinician submits an opinion.
"""
from apps.diagnosis.models import DoctorOpinion


class DoctorOpinionRepository:

    @staticmethod
    def create(diagnosis_id, text: str, submitted_by):
        """Create and return a new DoctorOpinion for the given diagnosis."""
        return DoctorOpinion.objects.create(
            diagnosis_id=diagnosis_id,
            text=text,
            submitted_by=submitted_by,
        )

    @staticmethod
    def get_by_diagnosis(diagnosis_id):
        """Returns DoctorOpinion for the given diagnosis_id, or None."""
        try:
            return DoctorOpinion.objects.select_related("submitted_by").get(
                diagnosis_id=diagnosis_id
            )
        except DoctorOpinion.DoesNotExist:
            return None
