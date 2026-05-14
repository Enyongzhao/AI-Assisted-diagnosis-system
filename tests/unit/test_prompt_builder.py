"""
Unit tests for PromptBuilder — design_doc §9.2

Verifies that build() includes all structured fields and free_text
in the returned prompt string.
"""
import pytest

from services.prompt_builder import PromptBuilder


STRUCTURED = {
    "age": 39,
    "gender": "male",
    "temperature": 38.5,
    "blood_pressure": "130/85",
    "heart_rate": 92,
    "symptoms": ["cough", "fatigue", "shortness_of_breath"],
    "duration_days": 5,
    "existing_conditions": ["hypertension"],
}
FREE_TEXT = "Patient reports worsening cough over 5 days."


class TestPromptBuilder:
    """design_doc §6 — PromptBuilder.build() output validation."""

    def test_prompt_contains_all_structured_fields(self):
        prompt = PromptBuilder.build(STRUCTURED, FREE_TEXT)
        assert "39" in prompt            # age
        assert "male" in prompt          # gender
        assert "38.5" in prompt          # temperature
        assert "130/85" in prompt        # blood_pressure
        assert "92" in prompt            # heart_rate
        assert "cough" in prompt         # symptoms[0]
        assert "fatigue" in prompt       # symptoms[1]
        assert "5" in prompt             # duration_days
        assert "hypertension" in prompt  # existing_conditions[0]

    def test_prompt_contains_free_text(self):
        prompt = PromptBuilder.build(STRUCTURED, FREE_TEXT)
        assert FREE_TEXT in prompt

    def test_prompt_requests_json_output(self):
        """design_doc §6 — LLM must return only a JSON object."""
        prompt = PromptBuilder.build(STRUCTURED, FREE_TEXT)
        assert "JSON" in prompt
        assert "summary" in prompt
        assert "differential_diagnosis" in prompt
        assert "recommended_investigations" in prompt
        assert "risk_factors" in prompt

    def test_empty_symptoms_shows_none_reported(self):
        data = dict(STRUCTURED, symptoms=[], existing_conditions=[])
        prompt = PromptBuilder.build(data, "")
        assert "none reported" in prompt.lower() or "none" in prompt.lower()

    def test_empty_free_text_handled_gracefully(self):
        prompt = PromptBuilder.build(STRUCTURED, "")
        assert isinstance(prompt, str)
        assert len(prompt) > 50
