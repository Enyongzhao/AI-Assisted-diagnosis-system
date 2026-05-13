"""
Patient serializers — design_doc §4.2
POST /api/v1/patients/ request/response shape.
"""
from rest_framework import serializers

from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    """
    design_doc §4.2 — full patient representation.
    created_by is set automatically from request.user in the view.
    """
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "date_of_birth",
            "gender",
            "contact_email",
            "linked_user",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_gender(self, value):
        allowed = {p[0] for p in Patient.GENDER_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError(
                f"gender must be one of: {', '.join(allowed)}"
            )
        return value
