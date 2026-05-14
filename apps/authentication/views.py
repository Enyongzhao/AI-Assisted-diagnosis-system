"""
Authentication views — design_doc §4.1
POST /api/v1/auth/login/           → access + refresh + user info
POST /api/v1/auth/refresh/         → new access token (delegated to simplejwt)
POST /api/v1/auth/change-password/ → change own password (any authenticated user)
"""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.serializers import LoginSerializer, UserSummarySerializer


class LoginView(APIView):
    """
    design_doc §4.1 — POST /api/v1/auth/login/
    Response 200: { access, refresh, user: { id, username, role } }
    Response 401: { detail: "Invalid credentials" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Return 401 for credential failures, 400 for malformed input
            errors = serializer.errors
            non_field = errors.get("non_field_errors", [])
            if any("Invalid credentials" in str(e) or "disabled" in str(e) for e in non_field):
                return Response(
                    {"detail": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSummarySerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Body: { current_password, new_password }
    Any authenticated user can change their own password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = request.data.get("current_password", "")
        new = request.data.get("new_password", "")

        if not current or not new:
            return Response(
                {"detail": "current_password and new_password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(current):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new) < 6:
            return Response(
                {"detail": "New password must be at least 6 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
