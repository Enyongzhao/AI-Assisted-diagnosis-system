"""
Repository layer for LLMReport — design_doc §5.1 llm_reports table.
Called by tasks/llm_task.py after the LLM call succeeds.
"""
from apps.diagnosis.models import LLMReport


class LLMReportRepository:

    @staticmethod
    def create(diagnosis_id, report_data: dict):
        """
        Persist the structured LLM output.

        report_data is the dict returned by LLMAdapter.generate(), containing:
          summary, differential_diagnosis, recommended_investigations, risk_factors,
          llm_provider, llm_model, prompt_tokens, completion_tokens, raw_response.
        """
        return LLMReport.objects.create(
            diagnosis_id=diagnosis_id,
            llm_provider=report_data["llm_provider"],
            llm_model=report_data["llm_model"],
            prompt_tokens=report_data["prompt_tokens"],
            completion_tokens=report_data["completion_tokens"],
            summary=report_data["summary"],
            differential_diagnosis=report_data["differential_diagnosis"],
            recommended_investigations=report_data["recommended_investigations"],
            risk_factors=report_data["risk_factors"],
            raw_response=report_data["raw_response"],
        )

    @staticmethod
    def get_by_diagnosis(diagnosis_id):
        """Returns LLMReport for the given diagnosis_id, or None."""
        try:
            return LLMReport.objects.get(diagnosis_id=diagnosis_id)
        except LLMReport.DoesNotExist:
            return None
