"""
RBAC permission classes — design_doc §1 "3 user roles: Admin, Clinician, Client"
Used as permission_classes on views; composable with | operator.
"""
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allow only users with role='admin'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsClinician(BasePermission):
    """Allow only users with role='clinician'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_clinician)


class IsClient(BasePermission):
    """Allow only users with role='client'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_client)


class IsAdminOrClinician(BasePermission):
    """Allow admin or clinician — used for patient endpoints."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("admin", "clinician")
        )
