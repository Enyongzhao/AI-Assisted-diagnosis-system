from django.contrib import admin
from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["name", "date_of_birth", "gender", "created_by", "is_deleted"]
    list_filter = ["gender", "is_deleted"]
