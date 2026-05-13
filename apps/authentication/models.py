"""
design_doc §5.1 — users table
Extends AbstractUser to add role-based access control (RBAC).
AUTH_USER_MODEL = 'authentication.User' in settings.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_CLINICIAN = "clinician"
    ROLE_CLIENT = "client"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CLINICIAN, "Clinician"),
        (ROLE_CLIENT, "Client"),
    ]

    # design_doc §1 — 3 user roles; default clinician for typical new accounts
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLINICIAN)

    # Make email unique as required by design_doc §5.1
    email = models.EmailField(unique=True)

    # AbstractUser already has date_joined (≈ created_at); add updated_at
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"

    # Convenience helpers used by permission classes and views
    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_clinician(self):
        return self.role == self.ROLE_CLINICIAN

    @property
    def is_client(self):
        return self.role == self.ROLE_CLIENT

    def __str__(self):
        return f"{self.username} ({self.role})"
