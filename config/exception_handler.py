"""
Custom DRF exception handler — implementation_plan.md 修复问题2 / Phase 1 Step 1.7
Maps domain exceptions to standard JSON error responses.
Phase 4 will fill in DuplicateSubmissionError and DiagnosisStatusError mappings.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    # Import here to avoid circular imports at module load time
    from apps.diagnosis.exceptions import DuplicateSubmissionError, DiagnosisStatusError

    # Let DRF handle its own exceptions first (ValidationError, PermissionDenied, etc.)
    response = exception_handler(exc, context)

    # design_doc §4.3 — DUPLICATE_SUBMISSION → 400
    if isinstance(exc, DuplicateSubmissionError):
        return Response(
            {
                "error": "DUPLICATE_SUBMISSION",
                "message": exc.message,
                "original_diagnosis_id": str(exc.original_diagnosis_id),
                "original_submitted_at": exc.original_submitted_at.isoformat(),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # design_doc §4.3 opinion endpoint — status machine violation → 400
    if isinstance(exc, DiagnosisStatusError):
        return Response(
            {"error": "INVALID_STATUS", "message": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return response
