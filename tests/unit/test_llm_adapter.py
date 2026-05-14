"""
Unit tests for LLMAdapter — design_doc §9.2 "LLM Adapter 路由测试"

Tests:
  - Claude adapter called when LLM_PROVIDER=claude
  - OpenAI adapter called when LLM_PROVIDER=openai
  - MockAdapter called when LLM_PROVIDER=mock
  - JSON parse failure raises JSONDecodeError
  - Unknown provider raises ValueError
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from adapters.llm_adapter import LLMAdapter


VALID_JSON_RESPONSE = json.dumps({
    "summary": "Test summary",
    "differential_diagnosis": ["Diagnosis A"],
    "recommended_investigations": ["Test X-ray"],
    "risk_factors": ["Risk 1"],
})


class TestLLMAdapterRouting:
    """design_doc §6 — LLMAdapter routes to correct provider."""

    @override_settings(LLM_PROVIDER="claude")
    @patch("adapters.llm_adapter.ClaudeAdapter.call")
    def test_claude_called_when_provider_is_claude(self, mock_call):
        mock_call.return_value = {
            "summary": "s", "differential_diagnosis": [],
            "recommended_investigations": [], "risk_factors": [],
            "llm_provider": "claude", "llm_model": "claude-sonnet-4-6",
            "prompt_tokens": 10, "completion_tokens": 20,
            "raw_response": {},
        }
        result = LLMAdapter.generate("test prompt")
        mock_call.assert_called_once_with("test prompt")
        assert result["llm_provider"] == "claude"

    @override_settings(LLM_PROVIDER="openai")
    @patch("adapters.llm_adapter.OpenAIAdapter.call")
    def test_openai_called_when_provider_is_openai(self, mock_call):
        mock_call.return_value = {
            "summary": "s", "differential_diagnosis": [],
            "recommended_investigations": [], "risk_factors": [],
            "llm_provider": "openai", "llm_model": "gpt-4o",
            "prompt_tokens": 10, "completion_tokens": 20,
            "raw_response": {},
        }
        result = LLMAdapter.generate("test prompt")
        mock_call.assert_called_once_with("test prompt")
        assert result["llm_provider"] == "openai"

    @override_settings(LLM_PROVIDER="mock")
    def test_mock_adapter_returns_deterministic_response(self):
        result = LLMAdapter.generate("any prompt")
        assert "summary" in result
        assert "differential_diagnosis" in result
        assert result["llm_provider"] == "mock"

    @override_settings(LLM_PROVIDER="unknown_provider")
    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            LLMAdapter.generate("test prompt")

    @override_settings(LLM_PROVIDER="claude")
    @patch("adapters.llm_adapter.ClaudeAdapter.call")
    def test_mock_call_returns_dict_not_string(self, mock_call):
        """Adapters return dicts directly (not raw JSON strings) since Phase 2."""
        mock_call.return_value = {
            "summary": "s", "differential_diagnosis": [],
            "recommended_investigations": [], "risk_factors": [],
            "llm_provider": "claude", "llm_model": "claude-sonnet-4-6",
            "prompt_tokens": 5, "completion_tokens": 10,
            "raw_response": {},
        }
        result = LLMAdapter.generate("prompt")
        assert isinstance(result, dict)
        assert "summary" in result


_VALID_LLM_JSON = json.dumps({
    "summary": "Test summary",
    "differential_diagnosis": ["Diagnosis A"],
    "recommended_investigations": ["X-ray"],
    "risk_factors": ["Risk 1"],
})


class TestClaudeAdapterCall:
    """Direct call to ClaudeAdapter.call() with mocked anthropic SDK."""

    @patch("anthropic.Anthropic")
    def test_call_returns_correct_structure(self, mock_anthropic_class):
        from adapters.llm_adapter import ClaudeAdapter

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_VALID_LLM_JSON)]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        result = ClaudeAdapter().call("test prompt")

        assert result["llm_provider"] == "claude"
        assert result["llm_model"] == "claude-sonnet-4-6"
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["summary"] == "Test summary"

    @patch("anthropic.Anthropic")
    def test_call_passes_prompt_to_sdk(self, mock_anthropic_class):
        from adapters.llm_adapter import ClaudeAdapter

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=_VALID_LLM_JSON)]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response

        ClaudeAdapter().call("my diagnosis prompt")

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["messages"][0]["content"] == "my diagnosis prompt"


class TestOpenAIAdapterCall:
    """Direct call to OpenAIAdapter.call() with mocked openai SDK."""

    @patch("openai.OpenAI")
    def test_call_returns_correct_structure(self, mock_openai_class):
        from adapters.llm_adapter import OpenAIAdapter

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = _VALID_LLM_JSON
        mock_response.usage.prompt_tokens = 80
        mock_response.usage.completion_tokens = 40
        mock_client.chat.completions.create.return_value = mock_response

        result = OpenAIAdapter().call("test prompt")

        assert result["llm_provider"] == "openai"
        assert result["llm_model"] == "gpt-4o"
        assert result["prompt_tokens"] == 80
        assert result["completion_tokens"] == 40
        assert result["summary"] == "Test summary"

    @patch("openai.OpenAI")
    def test_call_passes_prompt_to_sdk(self, mock_openai_class):
        from adapters.llm_adapter import OpenAIAdapter

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = _VALID_LLM_JSON
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response

        OpenAIAdapter().call("my diagnosis prompt")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"][0]["content"] == "my diagnosis prompt"
