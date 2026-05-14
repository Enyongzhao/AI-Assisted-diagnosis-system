"""
Global pytest fixtures — design_doc §9 "tests/conftest.py"

Provides reusable fixtures for all test layers:
  - Three users (admin, clinician, client)
  - One sample patient linked to the client user
  - Authenticated APIClient helpers for each role
"""
import pytest
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.patients.models import Patient


# ── User fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db):
    """design_doc §1 — Admin role user."""
    return User.objects.create_user(
        username="admin_user",
        email="admin@test.com",
        password="adminpass123",
        role=User.ROLE_ADMIN,
    )


@pytest.fixture
def clinician_user(db):
    """design_doc §1 — Clinician role user (submits diagnoses, writes opinions)."""
    return User.objects.create_user(
        username="dr_smith",
        email="drsmith@test.com",
        password="clinicianpass123",
        role=User.ROLE_CLINICIAN,
    )


@pytest.fixture
def client_user(db):
    """design_doc §1 — Client (patient) role user."""
    return User.objects.create_user(
        username="patient_01",
        email="patient01@test.com",
        password="clientpass123",
        role=User.ROLE_CLIENT,
    )


# ── Patient fixture ───────────────────────────────────────────────────────────

@pytest.fixture
def sample_patient(db, clinician_user, client_user):
    """design_doc §5.1 — Patient linked to client_user, created by clinician."""
    return Patient.objects.create(
        name="John Smith",
        date_of_birth="1985-03-22",
        gender="male",
        contact_email="john@test.com",
        linked_user=client_user,
        created_by=clinician_user,
    )


# ── Authenticated API clients ─────────────────────────────────────────────────

@pytest.fixture
def api_client():
    """Unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def admin_client(admin_user):
    """APIClient authenticated as admin."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def clinician_client(clinician_user):
    """APIClient authenticated as clinician."""
    client = APIClient()
    client.force_authenticate(user=clinician_user)
    return client


@pytest.fixture
def client_api_client(client_user):
    """APIClient authenticated as client (patient)."""
    client = APIClient()
    client.force_authenticate(user=client_user)
    return client


# ── Diagnosis submission payload ──────────────────────────────────────────────

@pytest.fixture
def diagnosis_payload(sample_patient):
    """Standard valid POST /api/v1/diagnosis/ payload."""
    return {
        "patient_id": sample_patient.id,
        "structured_data": {
            "age": 39,
            "gender": "male",
            "temperature": 38.5,
            "blood_pressure": "130/85",
            "heart_rate": 92,
            "symptoms": ["cough", "fatigue"],
            "duration_days": 5,
            "existing_conditions": ["hypertension"],
        },
        "free_text": "Patient reports worsening cough over 5 days.",
    }
