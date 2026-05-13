"""
Doctor opinion serializer — design_doc §4.3
PATCH /api/v1/diagnosis/{id}/opinion/ request body.
Implemented in Phase 2; defined here so urls.py can reference it.
"""
from rest_framework import serializers


class DoctorOpinionSerializer(serializers.Serializer):
    """design_doc §4.3 — { "text": "..." }"""
    text = serializers.CharField(min_length=1)
