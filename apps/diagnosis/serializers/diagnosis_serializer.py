"""
Diagnosis serializers — design_doc §4.3
Submit input, list response, detail response (with llm_report + doctor_opinion).
"""
from rest_framework import serializers

from apps.diagnosis.models import DiagnosisJob


# ── Input serializers (POST /api/v1/diagnosis/) ───────────────────────────────

class StructuredDataSerializer(serializers.Serializer):
    """
    design_doc §4.3 structured_data object in the request body.
    All fields optional so partial submissions are still accepted.
    """
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, default="")
    temperature = serializers.DecimalField(
        max_digits=4, decimal_places=1, required=False, allow_null=True
    )
    blood_pressure = serializers.CharField(required=False, allow_blank=True, default="")
    heart_rate = serializers.IntegerField(required=False, allow_null=True)
    symptoms = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    duration_days = serializers.IntegerField(required=False, allow_null=True)
    existing_conditions = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class DiagnosisSubmitSerializer(serializers.Serializer):
    """design_doc §4.3 POST /api/v1/diagnosis/ request body."""
    patient_id = serializers.IntegerField()
    structured_data = StructuredDataSerializer()
    free_text = serializers.CharField(required=False, allow_blank=True, default="")


# ── Output serializers ────────────────────────────────────────────────────────

class LLMReportSerializer(serializers.Serializer):
    """
    design_doc §4.3 — llm_report object in GET /api/v1/diagnosis/{id}/ response.
    Read from LLMReport model in Phase 2; null in Phase 1.
    """
    summary = serializers.CharField()
    differential_diagnosis = serializers.ListField(child=serializers.CharField())
    recommended_investigations = serializers.ListField(child=serializers.CharField())
    risk_factors = serializers.ListField(child=serializers.CharField())
    generated_by = serializers.CharField(source="llm_model")
    generated_at = serializers.DateTimeField()


class DoctorOpinionResponseSerializer(serializers.Serializer):
    """design_doc §4.3 — doctor_opinion object in the completed response."""
    text = serializers.CharField()
    submitted_by = serializers.CharField(source="submitted_by.username")
    submitted_at = serializers.DateTimeField()


class DiagnosisDetailSerializer(serializers.ModelSerializer):
    """
    design_doc §4.3 GET /api/v1/diagnosis/{id}/ — full detail with nested objects.
    llm_report and doctor_opinion are null until Phase 2 populates them.
    """
    diagnosis_id = serializers.UUIDField(source="id", read_only=True)
    llm_report = serializers.SerializerMethodField()
    doctor_opinion = serializers.SerializerMethodField()

    class Meta:
        model = DiagnosisJob
        fields = [
            "diagnosis_id",
            "status",
            "submitted_at",
            "llm_report",
            "doctor_opinion",
        ]

    def get_llm_report(self, obj):
        try:
            return LLMReportSerializer(obj.llm_report).data
        except Exception:
            return None

    def get_doctor_opinion(self, obj):
        try:
            return DoctorOpinionResponseSerializer(obj.doctor_opinion).data
        except Exception:
            return None


class DiagnosisListItemSerializer(serializers.ModelSerializer):
    """
    design_doc §4.3 GET /api/v1/diagnosis/ — compact list item.
    """
    diagnosis_id = serializers.UUIDField(source="id", read_only=True)
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = DiagnosisJob
        fields = ["diagnosis_id", "patient_id", "patient_name", "status", "submitted_at"]


class DiagnosisSubmitResponseSerializer(serializers.Serializer):
    """
    design_doc §4.3 — 202 response after POST /api/v1/diagnosis/
    Phase 1: LLM not yet wired; job sits at status=pending until Phase 2.
    """
    diagnosis_id = serializers.UUIDField()
    status = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    message = serializers.CharField()
    # Phase 2 will add warning fields here
    warning = serializers.CharField(required=False, allow_null=True)
    warning_message = serializers.CharField(required=False, allow_null=True)
    previous_diagnosis_id = serializers.UUIDField(required=False, allow_null=True)
