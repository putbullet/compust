"""
Compust AI Service Layer.

Delegates to the unified AI Gateway supporting both Ollama (local default)
and Google Gemini (cloud opt-in with explicit consent).
Preserves 100% backward-compatibility for all existing service callers.
"""

from typing import Any
from .ai_gateway import (
    AIGatewayError,
    AIUnavailableError,
    AIAuthenticationError,
    AIRateLimitError,
    AISafetyBlockError,
    AIConsentRequiredError,
    AIProviderType,
    OllamaError,
    OllamaUnavailableError,
    OllamaProvider,
    GeminiProvider,
    get_selected_model,
    set_selected_model,
    get_active_provider,
    set_active_provider,
    get_provider,
    get_ai_status,
    get_providers_list,
    generate_completion,
    generate_structured,
    get_gemini_api_key,
    set_gemini_api_key,
    mask_api_key,
    load_ai_config,
    save_ai_config,
    redact_personal_identifiers,
)


def get_configured_ollama_url() -> str:
    """Return the configured Ollama API endpoint."""
    return OllamaProvider.get_url()


def check_ollama_runtime(url: str | None = None) -> dict[str, Any]:
    """Check local Ollama daemon connectivity and discover installed models."""
    return OllamaProvider.check_health(url)


__all__ = [
    "AIGatewayError",
    "AIUnavailableError",
    "AIAuthenticationError",
    "AIRateLimitError",
    "AISafetyBlockError",
    "AIConsentRequiredError",
    "AIProviderType",
    "OllamaError",
    "OllamaUnavailableError",
    "OllamaProvider",
    "GeminiProvider",
    "get_provider",
    "get_selected_model",
    "set_selected_model",
    "get_active_provider",
    "set_active_provider",
    "get_ai_status",
    "get_providers_list",
    "generate_completion",
    "generate_structured",
    "get_gemini_api_key",
    "set_gemini_api_key",
    "mask_api_key",
    "load_ai_config",
    "save_ai_config",
    "redact_personal_identifiers",
    "get_configured_ollama_url",
    "check_ollama_runtime",
]
