"""
Opinion view — design_doc §4.3
PATCH /api/v1/diagnosis/{diagnosis_id}/opinion/

Clinician submits diagnosis opinion; triggers async PDF generation.
Only the Clinician who originally submitted the job can post an opinion.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsClinician
from apps.diagnosis.exceptions import DiagnosisStatusError
from apps.diagnosis.serializers.opinion_serializer import DoctorOpinionSerializer
from repositories.diagnosis_repository import DiagnosisRepository
from services.opinion_service import OpinionService


class DiagnosisOpinionView(APIView):
    """
    design_doc §4.3 PATCH /api/v1/diagnosis/{diagnosis_id}/opinion/

    Permission: IsClinician + ownership (submitted_by == request.user).
    Status machine: job must be in 'awaiting_doctor_input'.
    On success: fires generate_pdf_report.delay(); returns 200 + status=generating_pdf.
    """
    permission_classes = [IsClinician]

    def patch(self, request, diagnosis_id):
        serializer = DoctorOpinionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        job = DiagnosisRepository.get_by_id(diagnosis_id)
        if not job:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # design_doc §4.3 — only the submitting clinician can post an opinion
        if job.submitted_by_id != request.user.id:
            return Response(
                {"detail": "You do not have permission to submit an opinion for this diagnosis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            OpinionService.submit(
                diagnosis_id=diagnosis_id,
                text=serializer.validated_data["text"],
                submitted_by=request.user,
            )
        except DiagnosisStatusError as exc:
            return Response(
                {"detail": str(exc), "error": "INVALID_STATUS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "diagnosis_id": str(diagnosis_id),
                "status": "generating_pdf",
                "message": "Opinion saved. PDF generation in progress.",
            }
        )
