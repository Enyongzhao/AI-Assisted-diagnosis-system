"""
MockLLMAdapter — design_doc §9.4 "LLM_PROVIDER=mock for tests"

Used in E2E tests and anywhere that needs a deterministic LLM response
without making real API calls. Mirrors the dict structure returned by
ClaudeAdapter and OpenAIAdapter so callers are unaware of the difference.
"""


MOCK_REPORT = {
    "summary": (
        "Patient presents with cough, fatigue, and shortness of breath for 5 days. "
        "Elevated temperature and tachycardia suggest possible lower respiratory infection."
    ),
    "differential_diagnosis": [
        "Community-acquired pneumonia",
        "Acute bronchitis",
        "COVID-19",
    ],
    "recommended_investigations": [
        "Chest X-ray",
        "Full blood count",
        "CRP",
        "COVID-19 PCR",
    ],
    "risk_factors": ["Hypertension", "5-day symptom duration"],
    "llm_provider": "mock",
    "llm_model": "mock-llm",
    "prompt_tokens": 42,
    "completion_tokens": 85,
    "raw_response": {"content": "mock", "model": "mock-llm"},
}


class MockLLMAdapter:
    """Drop-in replacement for LLMAdapter — returns MOCK_REPORT for any prompt."""

    @staticmethod
    def generate(prompt: str) -> dict:  # noqa: ARG002
        return dict(MOCK_REPORT)
