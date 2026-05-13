"""
Patient CRUD views — design_doc §4.2
POST   /api/v1/patients/         → 201  (Clinician | Admin)
GET    /api/v1/patients/{id}/    → 200  (Clinician | Admin)
PUT    /api/v1/patients/{id}/    → 200  (Clinician | Admin)
DELETE /api/v1/patients/{id}/    → 204  (Admin only — soft delete)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin, IsAdminOrClinician
from apps.patients.serializers import PatientSerializer
from repositories.patient_repository import PatientRepository


class PatientListCreateView(APIView):
    """GET list + POST create — design_doc §4.2"""
    permission_classes = [IsAdminOrClinician]

    def get(self, request):
        patients = PatientRepository.list_active()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        patient = PatientRepository.create(
            name=serializer.validated_data["name"],
            date_of_birth=serializer.validated_data["date_of_birth"],
            gender=serializer.validated_data["gender"],
            contact_email=serializer.validated_data.get("contact_email"),
            linked_user=serializer.validated_data.get("linked_user"),
            created_by=request.user,
        )
        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)


class PatientDetailView(APIView):
    """GET / PUT / DELETE single patient — design_doc §4.2"""

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [IsAdmin()]
        return [IsAdminOrClinician()]

    def _get_patient_or_404(self, patient_id):
        patient = PatientRepository.get_by_id(patient_id)
        return patient  # None signals 404 to caller

    def get(self, request, patient_id):
        patient = self._get_patient_or_404(patient_id)
        if not patient:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PatientSerializer(patient).data)

    def put(self, request, patient_id):
        patient = self._get_patient_or_404(patient_id)
        if not patient:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated = PatientRepository.update(patient, **serializer.validated_data)
        return Response(PatientSerializer(updated).data)

    def delete(self, request, patient_id):
        """design_doc §4.2 — soft delete; Admin only (enforced by get_permissions)."""
        patient = self._get_patient_or_404(patient_id)
        if not patient:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        PatientRepository.soft_delete(patient)
        return Response(status=status.HTTP_204_NO_CONTENT)
