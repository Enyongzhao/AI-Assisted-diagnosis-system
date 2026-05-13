from django.contrib import admin

from apps.diagnosis.models import DiagnosisJob, DoctorOpinion, JobError, LLMReport, Report


@admin.register(DiagnosisJob)
class DiagnosisJobAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "submitted_by", "status", "submitted_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "submitted_at", "updated_at"]


@admin.register(LLMReport)
class LLMReportAdmin(admin.ModelAdmin):
    list_display = ["diagnosis", "llm_provider", "llm_model", "generated_at"]


@admin.register(DoctorOpinion)
class DoctorOpinionAdmin(admin.ModelAdmin):
    list_display = ["diagnosis", "submitted_by", "submitted_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["diagnosis", "s3_key", "generated_at"]


@admin.register(JobError)
class JobErrorAdmin(admin.ModelAdmin):
    list_display = ["diagnosis", "error_type", "retry_count", "occurred_at"]
