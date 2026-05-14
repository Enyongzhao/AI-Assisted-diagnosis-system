"""
Integration tests for patients API — design_doc §9.3 / §4.2

Tests:
  - Clinician can create a patient (201)
  - Client cannot create a patient (403)
  - Admin can soft-delete a patient (204)
  - Clinician cannot delete (403)
  - List, retrieve, update happy paths
"""
import pytest


@pytest.mark.django_db
class TestPatientCreate:
    """design_doc §4.2 POST /api/v1/patients/"""

    def test_clinician_can_create_patient(self, clinician_client):
        response = clinician_client.post("/api/v1/patients/", {
            "name": "Jane Doe",
            "date_of_birth": "1990-06-15",
            "gender": "female",
            "contact_email": "jane@test.com",
        }, format="json")

        assert response.status_code == 201
        assert response.data["name"] == "Jane Doe"

    def test_client_cannot_create_patient(self, client_api_client):
        response = client_api_client.post("/api/v1/patients/", {
            "name": "Unauthorized",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, format="json")

        assert response.status_code == 403

    def test_unauthenticated_cannot_create(self, api_client):
        response = api_client.post("/api/v1/patients/", {
            "name": "Anon",
            "date_of_birth": "1990-01-01",
            "gender": "male",
        }, format="json")

        assert response.status_code == 401

    def test_missing_required_fields_returns_400(self, clinician_client):
        response = clinician_client.post("/api/v1/patients/", {}, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestPatientRetrieve:
    """design_doc §4.2 GET /api/v1/patients/{id}/"""

    def test_clinician_can_retrieve_patient(self, clinician_client, sample_patient):
        response = clinician_client.get(f"/api/v1/patients/{sample_patient.id}/")
        assert response.status_code == 200
        assert response.data["name"] == "John Smith"

    def test_admin_can_retrieve_any_patient(self, admin_client, sample_patient):
        response = admin_client.get(f"/api/v1/patients/{sample_patient.id}/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestPatientDelete:
    """design_doc §4.2 DELETE /api/v1/patients/{id}/ — Admin only, soft delete."""

    def test_admin_can_soft_delete_patient(self, admin_client, sample_patient):
        response = admin_client.delete(f"/api/v1/patients/{sample_patient.id}/")
        assert response.status_code == 204

        # Soft-deleted patient should not appear in list
        from apps.patients.models import Patient
        sample_patient.refresh_from_db()
        assert sample_patient.is_deleted is True

    def test_clinician_cannot_delete_patient(self, clinician_client, sample_patient):
        response = clinician_client.delete(f"/api/v1/patients/{sample_patient.id}/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestPatientList:
    """GET /api/v1/patients/ — design_doc §4.2"""

    def test_clinician_can_list_patients(self, clinician_client, sample_patient):
        response = clinician_client.get("/api/v1/patients/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_admin_can_list_patients(self, admin_client, sample_patient):
        response = admin_client.get("/api/v1/patients/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestPatientUpdate:
    """PUT /api/v1/patients/{id}/ — design_doc §4.2"""

    def test_clinician_can_update_patient(self, clinician_client, sample_patient):
        response = clinician_client.put(
            f"/api/v1/patients/{sample_patient.id}/",
            {"name": "Updated Name", "date_of_birth": "1985-03-22", "gender": "male"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Name"

    def test_retrieve_nonexistent_returns_404(self, clinician_client):
        response = clinician_client.get("/api/v1/patients/999999/")
        assert response.status_code == 404

    def test_update_nonexistent_returns_404(self, clinician_client):
        response = clinician_client.put(
            "/api/v1/patients/999999/",
            {"name": "X", "date_of_birth": "1990-01-01", "gender": "male"},
            format="json",
        )
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, admin_client):
        response = admin_client.delete("/api/v1/patients/999999/")
        assert response.status_code == 404

    def test_update_with_invalid_data_returns_400(self, clinician_client, sample_patient):
        response = clinician_client.put(
            f"/api/v1/patients/{sample_patient.id}/",
            {"date_of_birth": "not-a-date"},
            format="json",
        )
        assert response.status_code == 400
