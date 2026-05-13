"""
Authentication views — design_doc §4.1
POST /api/v1/auth/login/   → access + refresh + user info
POST /api/v1/auth/refresh/ → new access token (delegated to simplejwt)
"""
from rest_framework import status
from rest_framework.permissions import AllowAny
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
