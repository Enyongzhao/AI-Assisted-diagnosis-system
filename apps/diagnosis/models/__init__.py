# Export all models so Django can discover them for migrations
from .diagnosis_job import DiagnosisJob
from .doctor_opinion import DoctorOpinion
from .job_error import JobError
from .llm_report import LLMReport
from .report import Report

__all__ = ["DiagnosisJob", "LLMReport", "DoctorOpinion", "Report", "JobError"]
