"""
Management command: create_test_users
Creates three role-based test accounts and one linked Patient record so that
all three roles (admin / clinician / client) can be used immediately after
`docker compose up`.

Usage:
    docker compose exec api python manage.py create_test_users

Accounts created:
    admin     / Admin123!   role=admin
    dr_smith  / Pass123!    role=clinician
    patient01 / Pass123!    role=client  ← linked to Patient "John Smith"

Re-running is idempotent: existing accounts are skipped, not overwritten.
"""
from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.patients.models import Patient


class Command(BaseCommand):
    help = "Seed three test accounts (admin / clinician / client) and a linked patient."

    def handle(self, *args, **options):
        # ── 1. Admin ─────────────────────────────────────────────────────────
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "role": User.ROLE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("Admin123!")
            admin.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("Created admin / Admin123!"))
        else:
            self.stdout.write("admin already exists — skipped")

        # ── 2. Clinician ─────────────────────────────────────────────────────
        clinician, created = User.objects.get_or_create(
            username="dr_smith",
            defaults={
                "email": "dr_smith@example.com",
                "role": User.ROLE_CLINICIAN,
            },
        )
        if created:
            clinician.set_password("Pass123!")
            clinician.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("Created dr_smith / Pass123!"))
        else:
            self.stdout.write("dr_smith already exists — skipped")

        # ── 3. Client ────────────────────────────────────────────────────────
        client, created = User.objects.get_or_create(
            username="patient01",
            defaults={
                "email": "patient01@example.com",
                "role": User.ROLE_CLIENT,
            },
        )
        if created:
            client.set_password("Pass123!")
            client.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("Created patient01 / Pass123!"))
        else:
            self.stdout.write("patient01 already exists — skipped")

        # ── 4. Patient record linked to the client account ───────────────────
        # design_doc §5.1 — linked_user connects a Patient to a Client account.
        # list_for_client() filters by patient__linked_user=user, so this link
        # is what lets the client see their own diagnosis records.
        patient, created = Patient.objects.get_or_create(
            name="John Smith",
            defaults={
                "date_of_birth": "1985-03-22",
                "gender": Patient.GENDER_MALE,
                "contact_email": "patient01@example.com",
                "linked_user": client,
                "created_by": clinician,
            },
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Patient 'John Smith' (id={patient.id}) linked to patient01"
                )
            )
        else:
            # Ensure linked_user is set even if patient already existed without it
            if patient.linked_user_id != client.id:
                patient.linked_user = client
                patient.save(update_fields=["linked_user"])
                self.stdout.write(
                    f"Patient 'John Smith' already existed — linked to patient01"
                )
            else:
                self.stdout.write("Patient 'John Smith' already exists and is linked — skipped")

        self.stdout.write(self.style.SUCCESS("\nDone. Test accounts:"))
        self.stdout.write("  admin     / Admin123!  (role=admin)")
        self.stdout.write("  dr_smith  / Pass123!   (role=clinician)")
        self.stdout.write(
            f"  patient01 / Pass123!   (role=client, linked patient id={patient.id})"
        )
        self.stdout.write(
            "\nWhen dr_smith submits a diagnosis for 'John Smith', "
            "patient01 can view and download the report."
        )
