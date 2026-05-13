"""
Report view — design_doc §4.3
GET /api/v1/diagnosis/{diagnosis_id}/report/

Returns a Pre-signed S3 URL (15-min expiry) for the generated PDF.
Access control mirrors DiagnosisDetailView RBAC rules.
"""
from datetime import datetime, timedelta, timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from adapters.s3_adapter import S3Adapter
from repositories.diagnosis_repository import DiagnosisRepository
from repositories.report_repository import ReportRepository


class DiagnosisReportView(APIView):
    """
    design_doc §4.3 GET /api/v1/diagnosis/{diagnosis_id}/report/

    Permission RBAC:
      - Admin: any diagnosis
      - Clinician: only diagnoses they submitted
      - Client: only diagnoses belonging to their linked patient
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, diagnosis_id):
        job = DiagnosisRepository.get_by_id(diagnosis_id)
        if not job:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # design_doc §4.3 — enforce per-role data access boundaries
        user = request.user
        if user.is_clinician and job.submitted_by_id != user.id:
            return Response(
                {"detail": "You do not have permission to access this report."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.is_client and job.patient.linked_user_id != user.id:
            return Response(
                {"detail": "You do not have permission to access this report."},
                status=status.HTTP_403_FORBIDDEN,
            )

        report = ReportRepository.get_by_diagnosis(diagnosis_id)
        if not report:
            return Response(
                {"detail": "Report not yet generated. Check diagnosis status."},
                status=status.HTTP_404_NOT_FOUND,
            )

        pdf_url = S3Adapter.generate_presigned_url(report.s3_key)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=S3Adapter.PRESIGNED_URL_EXPIRY)

        return Response(
            {
                "diagnosis_id": str(diagnosis_id),
                "pdf_url": pdf_url,
                "expires_at": expires_at.isoformat(),
            }
        )
