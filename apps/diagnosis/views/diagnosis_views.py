"""
Diagnosis views — design_doc §4.3

POST   /api/v1/diagnosis/          → 202  creates job, fires generate_llm_report.delay()
GET    /api/v1/diagnosis/          → 200  paginated list (role-filtered)
GET    /api/v1/diagnosis/{id}/     → 200  detail / polling endpoint
"""
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsClinician
from apps.diagnosis.serializers.diagnosis_serializer import (
    DiagnosisDetailSerializer,
    DiagnosisListItemSerializer,
    DiagnosisSubmitSerializer,
)

from repositories.diagnosis_repository import DiagnosisRepository
from repositories.patient_repository import PatientRepository
from services.diagnosis_service import DiagnosisService


class DiagnosisPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DiagnosisListCreateView(APIView):
    """
    design_doc §4.3 — both methods live at /api/v1/diagnosis/

    POST (Clinician only) — creates DiagnosisJob, returns 202 + diagnosis_id.
      Phase 2 will call generate_llm_report.delay(diagnosis_id) here.

    GET (all authenticated roles) — paginated list, role-filtered.
      - Admin   → all jobs
      - Clinician → own submissions
      - Client  → jobs for their linked patient
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsClinician()]
        return [IsAuthenticated()]

    def post(self, request):
        serializer = DiagnosisSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        patient = PatientRepository.get_by_id(data["patient_id"])
        if not patient:
            return Response(
                {"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # design_doc §4.3 Phase 4 — DiagnosisService handles duplicate detection +
        # job creation + firing generate_llm_report.delay().
        # DuplicateSubmissionError (Hard Error) is not caught here — it propagates
        # to custom_exception_handler which returns HTTP 400.
        result = DiagnosisService.submit(
            patient=patient,
            submitted_by=request.user,
            structured_data=data["structured_data"],
            free_text=data.get("free_text", ""),
        )

        job = result["job"]
        response_body = {
            "diagnosis_id": str(job.id),
            "status": job.status,
            "submitted_at": job.submitted_at.isoformat(),
            "message": "LLM report generation in progress. Poll /api/v1/diagnosis/{id}/ for result.",
        }

        # design_doc §4.3 — Soft Warning: include warning fields in 202 response
        if result["has_warning"]:
            response_body["warning"] = result["warning_type"]
            response_body["warning_message"] = result["warning_message"]
            response_body["previous_diagnosis_id"] = str(result["previous_diagnosis_id"])

        return Response(response_body, status=status.HTTP_202_ACCEPTED)

    def get(self, request):
        user = request.user

        # Role-based queryset selection
        if user.is_admin:
            qs = DiagnosisRepository.list_all()
        elif user.is_clinician:
            qs = DiagnosisRepository.list_for_clinician(user)
        else:
            qs = DiagnosisRepository.list_for_client(user)

        # Optional filters
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        patient_id_filter = request.query_params.get("patient_id")
        if patient_id_filter:
            qs = qs.filter(patient_id=patient_id_filter)

        paginator = DiagnosisPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DiagnosisListItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class DiagnosisDetailView(APIView):
    """
    design_doc §4.3 GET /api/v1/diagnosis/{diagnosis_id}/
    Polling endpoint — returns current status + llm_report + doctor_opinion.
    Access control: Admin sees any; Clinician sees own; Client sees own patient.
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
                {"detail": "You do not have permission to view this diagnosis."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user.is_client and job.patient.linked_user_id != user.id:
            return Response(
                {"detail": "You do not have permission to view this diagnosis."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(DiagnosisDetailSerializer(job).data)
