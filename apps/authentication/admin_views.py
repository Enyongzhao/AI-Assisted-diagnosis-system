"""
User management views for Admin — design_doc §4.4
All endpoints restricted to IsAdmin.
GET/POST  /api/v1/users/
GET/PUT/DELETE /api/v1/users/{id}/
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import User
from apps.authentication.permissions import IsAdmin
from apps.authentication.serializers import UserSerializer


class UserListCreateView(APIView):
    """
    design_doc §4.4
    GET  — list all users
    POST — create a new user with role assignment
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.filter(is_active=True).order_by("id")
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        # Ensure password is set if provided in request
        password = request.data.get("password")
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    """
    design_doc §4.4
    PUT    — update user info / role
    DELETE — soft-deactivate user account (is_active=False)
    """
    permission_classes = [IsAdmin]

    def _get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    def get(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data)

    def put(self, request, user_id):
        user = self._get_user(user_id)
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, user_id):
        """design_doc §4.4 — soft-delete: set is_active=False."""
        user = self._get_user(user_id)
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
