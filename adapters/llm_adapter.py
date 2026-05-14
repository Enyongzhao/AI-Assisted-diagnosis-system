"""
LLM Adapter — design_doc §6 "LLM Adapter pattern"

LLMAdapter.generate(prompt) is the single entry point for all business logic.
Routes to ClaudeAdapter / OpenAIAdapter / MockAdapter based on settings.LLM_PROVIDER.

Each adapter's call() returns a dict with both the parsed clinical fields AND
request metadata (provider, model, token counts, raw_response) so the caller
can persist everything to llm_reports in one shot.
"""
import json

from django.conf import settings


class LLMAdapter:
    """Unified LLM interface — business layer never sees provider details."""

    @staticmethod
    def generate(prompt: str) -> dict:
        """
        Call the configured LLM provider and return a fully-populated dict:
          {
            "summary": str,
            "differential_diagnosis": [...],
            "recommended_investigations": [...],
            "risk_factors": [...],
            "llm_provider": str,
            "llm_model": str,
            "prompt_tokens": int,
            "completion_tokens": int,
            "raw_response": dict,
          }
        """
        provider = settings.LLM_PROVIDER
        if provider == "claude":
            return ClaudeAdapter().call(prompt)
        elif provider == "openai":
            return OpenAIAdapter().call(prompt)
        elif provider == "mock":
            return MockAdapter().call(prompt)
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")


class ClaudeAdapter:
    """design_doc §6 — wraps anthropic.Anthropic SDK."""

    MODEL = "claude-sonnet-4-6"

    def call(self, prompt: str) -> dict:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        response = client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text
        parsed = json.loads(raw_text)

        return {
            **parsed,
            "llm_provider": "claude",
            "llm_model": self.MODEL,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "raw_response": {"content": raw_text, "model": self.MODEL},
        }


class OpenAIAdapter:
    """design_doc §6 — wraps openai SDK."""

    MODEL = "gpt-4o"

    def call(self, prompt: str) -> dict:
        import openai

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=self.MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        parsed = json.loads(raw_text)

        return {
            **parsed,
            "llm_provider": "openai",
            "llm_model": self.MODEL,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "raw_response": {"content": raw_text, "model": self.MODEL},
        }


class MockAdapter:
    """
    design_doc §9.4 — LLM_PROVIDER=mock for local dev and tests.
    Returns a deterministic JSON structure without calling any external API.
    """

    MODEL = "mock-llm"

    def call(self, prompt: str) -> dict:
        parsed = {
            "summary": (
                "Mock analysis: Patient presents with reported symptoms. "
                "This is a test response — set LLM_PROVIDER=claude or openai for real results."
            ),
            "differential_diagnosis": [
                "Diagnosis A (mock)",
                "Diagnosis B (mock)",
                "Diagnosis C (mock)",
            ],
            "recommended_investigations": [
                "Full blood count (mock)",
                "Chest X-ray (mock)",
            ],
            "risk_factors": ["Mock risk factor 1", "Mock risk factor 2"],
        }
        return {
            **parsed,
            "llm_provider": "mock",
            "llm_model": self.MODEL,
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 50,
            "raw_response": {"content": json.dumps(parsed), "model": self.MODEL},
        }
