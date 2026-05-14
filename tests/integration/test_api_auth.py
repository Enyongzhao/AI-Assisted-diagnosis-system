"""
Integration tests for auth API — design_doc §9.3 / §4.1

Tests:
  - POST /api/v1/auth/login/ success → returns access + refresh + user info
  - POST /api/v1/auth/login/ wrong password → 401
  - POST /api/v1/auth/refresh/ → new access token
"""
import pytest


@pytest.mark.django_db
class TestAuthLogin:
    """design_doc §4.1 POST /api/v1/auth/login/"""

    def test_login_success_returns_tokens_and_user(self, api_client, clinician_user):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "dr_smith",
            "password": "clinicianpass123",
        }, format="json")

        assert response.status_code == 200
        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["username"] == "dr_smith"
        assert data["user"]["role"] == "clinician"

    def test_login_wrong_password_returns_401(self, api_client, clinician_user):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "dr_smith",
            "password": "wrongpassword",
        }, format="json")

        assert response.status_code == 401

    def test_login_nonexistent_user_returns_401(self, api_client):
        response = api_client.post("/api/v1/auth/login/", {
            "username": "nobody",
            "password": "pass",
        }, format="json")

        assert response.status_code == 401

    def test_login_missing_fields_returns_400(self, api_client):
        response = api_client.post("/api/v1/auth/login/", {}, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestAuthTokenRefresh:
    """design_doc §4.1 POST /api/v1/auth/refresh/"""

    def test_refresh_returns_new_access_token(self, api_client, clinician_user):
        # First login to get refresh token
        login_resp = api_client.post("/api/v1/auth/login/", {
            "username": "dr_smith",
            "password": "clinicianpass123",
        }, format="json")
        refresh_token = login_resp.data["refresh"]

        # Use refresh token to get new access token
        response = api_client.post("/api/v1/auth/refresh/", {
            "refresh": refresh_token,
        }, format="json")

        assert response.status_code == 200
        assert "access" in response.data

    def test_refresh_with_invalid_token_returns_401(self, api_client):
        response = api_client.post("/api/v1/auth/refresh/", {
            "refresh": "invalid.token.here",
        }, format="json")

        assert response.status_code == 401


@pytest.mark.django_db
class TestChangePassword:
    """POST /api/v1/auth/change-password/"""

    def test_change_password_success(self, clinician_client, clinician_user):
        response = clinician_client.post("/api/v1/auth/change-password/", {
            "current_password": "clinicianpass123",
            "new_password": "newpassword456",
        }, format="json")
        assert response.status_code == 200
        assert "Password changed" in response.data["detail"]

    def test_change_password_wrong_current(self, clinician_client, clinician_user):
        response = clinician_client.post("/api/v1/auth/change-password/", {
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
        }, format="json")
        assert response.status_code == 400

    def test_change_password_too_short(self, clinician_client, clinician_user):
        response = clinician_client.post("/api/v1/auth/change-password/", {
            "current_password": "clinicianpass123",
            "new_password": "abc",
        }, format="json")
        assert response.status_code == 400

    def test_change_password_missing_fields(self, clinician_client):
        response = clinician_client.post("/api/v1/auth/change-password/", {}, format="json")
        assert response.status_code == 400

    def test_unauthenticated_cannot_change_password(self, api_client):
        response = api_client.post("/api/v1/auth/change-password/", {
            "current_password": "pass",
            "new_password": "newpassword456",
        }, format="json")
        assert response.status_code == 401
