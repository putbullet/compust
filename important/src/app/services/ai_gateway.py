"""
Compust Unified AI Gateway Abstraction.

Provides a unified interface for LLM operations across multiple providers:
1. Ollama (Local, offline, privacy-first default)
2. Google Gemini (Cloud, high-reasoning, requires user consent and API key)

Key Principles:
- Local-First Default: Ollama is always the default provider.
- Explicit Privacy & Consent: Using Gemini requires explicit user consent.
- Strict PII Redaction: Personal identifiers (email, phone, URLs) are redacted
  from prompts for tasks that do not require identity.
- Write-Only Key Security: API keys are stored securely server-side and never returned
  in full to the frontend, extension, or logs.
- Zero Silent Cross-Provider Fallback: Ollama failures never silently route to Gemini,
  and Gemini failures never route to Ollama unless explicitly enabled by user.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings
from ..logging import get_logger
from ..paths import get_user_data_dir

logger = get_logger(__name__)


# ─── Enums & Exceptions ─────────────────────────────────────────────────────────

class AIProviderType(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"


class AIGatewayError(Exception):
    """Base exception for all AI Gateway errors."""
    pass


class AIUnavailableError(AIGatewayError):
    """Raised when an AI provider is unreachable, offline, or timed out."""
    pass


class AIAuthenticationError(AIGatewayError):
    """Raised when API key or credentials are invalid or missing."""
    pass


class AIRateLimitError(AIGatewayError):
    """Raised when an AI provider rate limit or quota is exhausted."""
    pass


class AISafetyBlockError(AIGatewayError):
    """Raised when output or prompt was blocked by content safety filters."""
    pass


class AIConsentRequiredError(AIGatewayError):
    """Raised when cloud processing was requested without explicit user consent."""
    pass


# Compatibility aliases for existing Ollama callers
OllamaError = AIGatewayError
OllamaUnavailableError = AIUnavailableError


# ─── PII Redaction Discipline ──────────────────────────────────────────────────

_EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
_PHONE_REGEX = re.compile(
    r"\b0[1-9](?:[-.\s]?\d{2}){4}\b|"
    r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b|"
    r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
_URL_REGEX = re.compile(r"https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*")


def redact_personal_identifiers(text: str) -> str:
    """
    Strips email addresses, phone numbers, and URLs from prompt text
    to minimize PII exposure when querying external models.
    """
    if not text:
        return ""
    redacted = _EMAIL_REGEX.sub("[email-redacted]", text)
    redacted = _PHONE_REGEX.sub("[phone-redacted]", redacted)
    redacted = _URL_REGEX.sub("[url-redacted]", redacted)
    return redacted


def mask_api_key(key: str | None) -> str:
    """Return a masked representation of an API key for safe display (last 4 chars only)."""
    if not key or len(key) < 6:
        return ""
    return f"...{key[-4:]}"


# ─── Persistent AI Configuration & Credential Store ────────────────────────────

def get_ai_config_path() -> Path:
    return get_user_data_dir() / "ai_config.json"


def load_ai_config() -> dict[str, Any]:
    """Load AI provider settings and credentials from user data directory."""
    cfg_file = get_ai_config_path()
    default_cfg: dict[str, Any] = {
        "active_provider": AIProviderType.OLLAMA.value,
        "selected_model": "qwen3.5:0.8b",
        "gemini_model": "gemini-3.8-flash",
        "gemini_consent_given": False,
        "fallback_policy": "deterministic",  # 'deterministic' | 'error' | 'try_other'
    }
    if cfg_file.is_file():
        try:
            stored = json.loads(cfg_file.read_text(encoding="utf-8"))
            default_cfg.update(stored)
        except Exception as e:
            logger.warning(f"Could not parse {cfg_file}: {e}")
    return default_cfg


def _dpapi_encrypt(plaintext: str) -> str:
    """Encrypt a string using Windows DPAPI if running on Windows."""
    if sys.platform != "win32":
        return plaintext
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte)),
            ]

        data_bytes = plaintext.encode("utf-8")
        blob_in = DATA_BLOB(len(data_bytes), ctypes.cast(data_bytes, ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()

        crypt32 = ctypes.windll.crypt32
        if crypt32.CryptProtectData(ctypes.byref(blob_in), "compust_gemini_key", None, None, None, 0, ctypes.byref(blob_out)):
            out_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return "dpapi:" + base64.b64encode(out_bytes).decode("ascii")
    except Exception as e:
        logger.warning(f"DPAPI encryption failed, falling back: {e}")
    return plaintext


def _dpapi_decrypt(ciphertext: str) -> str:
    """Decrypt a DPAPI-encrypted string if running on Windows."""
    if not ciphertext.startswith("dpapi:") or sys.platform != "win32":
        return ciphertext
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte)),
            ]

        raw = base64.b64decode(ciphertext[6:])
        blob_in = DATA_BLOB(len(raw), ctypes.cast(raw, ctypes.POINTER(ctypes.c_byte)))
        blob_out = DATA_BLOB()

        crypt32 = ctypes.windll.crypt32
        if crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
            out_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return out_bytes.decode("utf-8")
    except Exception as e:
        logger.warning(f"DPAPI decryption failed: {e}")
    return ciphertext


def save_ai_config(cfg: dict[str, Any]) -> None:
    """Persist AI provider settings to user data directory with restricted permissions."""
    cfg_file = get_ai_config_path()
    try:
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        if sys.platform != "win32":
            try:
                os.chmod(cfg_file, 0o600)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to write AI configuration to {cfg_file}: {e}")


def get_gemini_api_key() -> str | None:
    """
    Retrieve Google Gemini API key from:
    1. Local persistent user configuration (highest precedence, set in Settings UI)
    2. Environment variable GEMINI_API_KEY
    3. Untracked local .env file
    """
    cfg = load_ai_config()
    # 1. DPAPI encrypted key in config
    enc_key = (cfg.get("gemini_api_key_encrypted") or "").strip()
    if enc_key:
        dec = _dpapi_decrypt(enc_key)
        if dec:
            return dec

    # 2. Plain text key in config (legacy or non-Windows)
    cfg_key = (cfg.get("gemini_api_key") or "").strip()
    if cfg_key:
        return cfg_key

    # 3. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    # 4. Untracked local .env file
    for candidate in [Path(".env"), Path(__file__).resolve().parents[3] / ".env"]:
        try:
            if candidate.is_file():
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass

    return None


def set_gemini_api_key(key: str | None) -> None:
    """Store or clear the Gemini API key in user configuration with DPAPI protection."""
    cfg = load_ai_config()
    if key and key.strip():
        k = key.strip()
        enc = _dpapi_encrypt(k)
        if enc.startswith("dpapi:"):
            cfg["gemini_api_key_encrypted"] = enc
            cfg.pop("gemini_api_key", None)
        else:
            cfg["gemini_api_key"] = k
    else:
        cfg.pop("gemini_api_key", None)
        cfg.pop("gemini_api_key_encrypted", None)
    save_ai_config(cfg)


# ─── Provider Implementations ──────────────────────────────────────────────────

class OllamaProvider:
    """Local, offline Ollama provider."""

    @staticmethod
    def get_url() -> str:
        settings = get_settings()
        return settings.ollama_url.rstrip("/")

    @classmethod
    def check_health(cls, url: str | None = None) -> dict[str, Any]:
        target_url = (url or cls.get_url()).rstrip("/")
        status_data: dict[str, Any] = {
            "provider": "ollama",
            "name": "Ollama (Local)",
            "url": target_url,
            "status": "unavailable",
            "models": [],
            "selected_model": get_selected_model(),
            "selected_model_available": False,
            "error": None,
            "is_local": True,
        }
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{target_url}/api/tags")
                if resp.status_code == 200:
                    raw_models = resp.json().get("models", [])
                    models_list = []
                    for m in raw_models:
                        name = m.get("name") or m.get("model")
                        if name:
                            models_list.append({
                                "name": name,
                                "size": m.get("size", 0),
                                "modified_at": m.get("modified_at"),
                                "parameter_size": m.get("details", {}).get("parameter_size"),
                                "quantization_level": m.get("details", {}).get("quantization_level"),
                            })
                    status_data["status"] = "connected"
                    status_data["models"] = models_list

                    installed_names = [m["name"] for m in models_list]
                    current_selected = get_selected_model()
                    if not current_selected and installed_names:
                        current_selected = installed_names[0]
                        set_selected_model(current_selected)

                    status_data["selected_model"] = current_selected
                    status_data["selected_model_available"] = (
                        current_selected in installed_names if current_selected else False
                    )
                else:
                    status_data["status"] = "unavailable"
                    status_data["error"] = f"HTTP {resp.status_code}: {resp.text}"
        except httpx.ConnectError:
            status_data["status"] = "not_running"
            status_data["error"] = f"Could not connect to Ollama at {target_url}. Is Ollama running?"
        except httpx.TimeoutException:
            status_data["status"] = "timeout"
            status_data["error"] = f"Connection to Ollama timed out at {target_url}"
        except Exception as exc:
            status_data["status"] = "unavailable"
            status_data["error"] = str(exc)

        return status_data

    @classmethod
    def test_connection(cls, model: str | None = None) -> dict[str, Any]:
        target_url = cls.get_url()
        target_model = model or get_selected_model()
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{target_url}/api/tags")
                latency = int((time.perf_counter() - t0) * 1000)
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name") for m in models]
                    if target_model and target_model not in model_names:
                        return {
                            "success": True,
                            "provider": "ollama",
                            "model": target_model,
                            "message": f"Ollama is running ({latency}ms), but model '{target_model}' is not installed locally. Run: ollama pull {target_model}",
                            "latency_ms": latency,
                        }
                    return {
                        "success": True,
                        "provider": "ollama",
                        "model": target_model,
                        "message": f"Connected to local Ollama daemon ({len(models)} models available, {latency}ms).",
                        "latency_ms": latency,
                    }
                return {
                    "success": False,
                    "provider": "ollama",
                    "model": target_model,
                    "message": f"Ollama returned HTTP {resp.status_code}",
                    "latency_ms": latency,
                }
        except httpx.ConnectError:
            return {
                "success": False,
                "provider": "ollama",
                "model": target_model,
                "message": f"Could not connect to Ollama at {target_url}. Is Ollama running?",
                "latency_ms": None,
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "ollama",
                "model": target_model,
                "message": f"Ollama connection test failed: {str(e)}",
                "latency_ms": None,
            }

    @classmethod
    def generate(
        cls,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        timeout_seconds: float = 45.0,
        response_json: bool = False,
    ) -> str:
        url = cls.get_url()
        target_model = model or get_selected_model()

        if not target_model:
            health = cls.check_health(url)
            if health["models"]:
                target_model = health["models"][0]["name"]
                set_selected_model(target_model)
            else:
                raise AIUnavailableError("No Ollama models installed or available. Run 'ollama pull qwen3.5:0.8b'.")

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if response_json:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(f"{url}/api/generate", json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("response", "").strip()
                raise AIGatewayError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise AIUnavailableError(f"Cannot reach Ollama at {url}: {exc}") from exc
        except Exception as exc:
            raise AIGatewayError(f"Ollama generation failed: {exc}") from exc

    @classmethod
    def is_available(cls) -> bool:
        health = cls.check_health()
        return health.get("status") == "connected" and bool(health.get("models"))

    @classmethod
    def get_active_model(cls) -> str:
        return get_selected_model() or "qwen3.5:0.8b"


class GeminiProvider:
    """Google Gemini Cloud AI Provider using direct HTTPS REST API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    RECOMMENDED_MODELS = [
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (Recommended)", "recommended": True},
        {"id": "gemini-flash-latest", "name": "Gemini Flash (Latest Release)", "recommended": False},
        {"id": "gemini-flash-lite-latest", "name": "Gemini Flash Lite (Fast & Efficient)", "recommended": False},
        {"id": "gemini-pro-latest", "name": "Gemini Pro (Deep Reasoning)", "recommended": False},
    ]

    @classmethod
    def test_connection(cls, api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
        key = api_key or get_gemini_api_key()
        cfg = load_ai_config()
        target_model = model or cfg.get("gemini_model") or "gemini-3.8-flash"
        if not key:
            return {
                "success": False,
                "provider": "gemini",
                "model": target_model,
                "message": "No Google Gemini API key provided. Please enter an API key.",
                "latency_ms": None,
            }
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                url = f"{cls.BASE_URL}/models/{target_model}:generateContent"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": "Ping"}]}],
                    "generationConfig": {"maxOutputTokens": 5},
                }
                resp = client.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=payload,
                )
                latency = int((time.perf_counter() - t0) * 1000)
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "provider": "gemini",
                        "model": target_model,
                        "message": f"Successfully connected to Google Gemini ({target_model}) in {latency}ms.",
                        "latency_ms": latency,
                    }
                if resp.status_code in (401, 403) or "API_KEY" in resp.text:
                    return {
                        "success": False,
                        "provider": "gemini",
                        "model": target_model,
                        "message": "Invalid Google Gemini API key. Please check your credentials.",
                        "latency_ms": latency,
                    }
                if resp.status_code == 429:
                    return {
                        "success": False,
                        "provider": "gemini",
                        "model": target_model,
                        "message": "Google Gemini quota or rate limit exceeded.",
                        "latency_ms": latency,
                    }
                if resp.status_code == 404:
                    return {
                        "success": False,
                        "provider": "gemini",
                        "model": target_model,
                        "message": f"Model '{target_model}' not found or deprecated by Google. Try 'gemini-3.8-flash'.",
                        "latency_ms": latency,
                    }
                return {
                    "success": False,
                    "provider": "gemini",
                    "model": target_model,
                    "message": f"Google Gemini returned HTTP {resp.status_code}: {resp.text[:120]}",
                    "latency_ms": latency,
                }
        except httpx.ConnectError:
            return {
                "success": False,
                "provider": "gemini",
                "model": target_model,
                "message": "Cannot reach Google Gemini. Please check your internet connection.",
                "latency_ms": None,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "provider": "gemini",
                "model": target_model,
                "message": "Connection to Google Gemini timed out (10s limit).",
                "latency_ms": None,
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "gemini",
                "model": target_model,
                "message": f"Connection test failed: {str(e)}",
                "latency_ms": None,
            }

    @classmethod
    def check_health(cls, api_key: str | None = None) -> dict[str, Any]:
        key = api_key or get_gemini_api_key()
        cfg = load_ai_config()

        status_data: dict[str, Any] = {
            "provider": "gemini",
            "name": "Google Gemini (Cloud)",
            "status": "not_configured" if not key else "configured",
            "models": cls.RECOMMENDED_MODELS,
            "selected_model": cfg.get("gemini_model", "gemini-3.8-flash"),
            "key_hint": mask_api_key(key),
            "consent_given": cfg.get("gemini_consent_given", False),
            "error": None,
            "is_local": False,
        }

        if not key:
            status_data["status"] = "not_configured"
            status_data["error"] = "No Gemini API key configured. Enter an API key in Settings."
            return status_data

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    f"{cls.BASE_URL}/models",
                    headers={"x-goog-api-key": key},
                )
                if resp.status_code == 200:
                    status_data["status"] = "connected"
                elif resp.status_code in (401, 403):
                    status_data["status"] = "invalid_key"
                    status_data["error"] = "Invalid Google Gemini API key. Please check your credentials."
                elif resp.status_code == 429:
                    status_data["status"] = "rate_limited"
                    status_data["error"] = "Gemini API rate limit or quota exceeded."
                else:
                    status_data["status"] = "error"
                    status_data["error"] = f"HTTP {resp.status_code}: {resp.text}"
        except httpx.ConnectError:
            status_data["status"] = "network_error"
            status_data["error"] = "Cannot reach Google Gemini API. Check your internet connection."
        except httpx.TimeoutException:
            status_data["status"] = "timeout"
            status_data["error"] = "Connection to Google Gemini API timed out."
        except Exception as exc:
            status_data["status"] = "error"
            status_data["error"] = str(exc)

        return status_data

    @classmethod
    def generate(
        cls,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        timeout_seconds: float = 45.0,
        response_json: bool = False,
    ) -> str:
        key = get_gemini_api_key()
        if not key:
            raise AIAuthenticationError("Google Gemini API key not configured. Add a key in AI Settings.")

        cfg = load_ai_config()
        if not cfg.get("gemini_consent_given", False):
            raise AIConsentRequiredError(
                "Cloud processing consent required before sending queries to Google Gemini. "
                "Enable consent in AI Settings."
            )

        target_model = model or cfg.get("gemini_model") or "gemini-3.8-flash"
        url = f"{cls.BASE_URL}/models/{target_model}:generateContent"

        # Build payload with systemInstruction and contents
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        if response_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        # Resilience: Retry with backoff on 429 / 5xx
        max_attempts = 3
        backoff_delays = [1.0, 2.0, 4.0]

        for attempt in range(max_attempts):
            try:
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(
                        url,
                        headers={
                            "x-goog-api-key": key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        prompt_feedback = data.get("promptFeedback", {})
                        block_reason = prompt_feedback.get("blockReason")
                        if block_reason:
                            raise AISafetyBlockError(f"Prompt blocked by Google Gemini safety filters ({block_reason}).")
                        raise AIGatewayError("Google Gemini returned an empty candidate list.")

                    first = candidates[0]
                    if first.get("finishReason") == "SAFETY":
                        raise AISafetyBlockError("Output blocked by Google Gemini content safety filters.")

                    parts = first.get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    return text.strip()

                if resp.status_code in (401, 403) or (
                    resp.status_code == 400
                    and (
                        "API_KEY" in resp.text
                        or "API key not valid" in resp.text
                        or "INVALID_ARGUMENT" in resp.text
                    )
                ):
                    raise AIAuthenticationError("Invalid or unauthorized Google Gemini API key.")

                if resp.status_code == 429:
                    if attempt < max_attempts - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise AIRateLimitError("Google Gemini quota or rate limit exceeded. Please try again later.")

                if resp.status_code in (500, 502, 503, 504):
                    if attempt < max_attempts - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise AIUnavailableError(f"Google Gemini service unavailable (HTTP {resp.status_code}).")

                raise AIGatewayError(f"Google Gemini returned HTTP {resp.status_code}: {resp.text}")

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < max_attempts - 1:
                    time.sleep(backoff_delays[attempt])
                    continue
                raise AIUnavailableError(f"Connection to Google Gemini failed: {exc}") from exc
            except (AIGatewayError, AIAuthenticationError, AIRateLimitError, AISafetyBlockError, AIConsentRequiredError):
                raise
            except Exception as exc:
                raise AIGatewayError(f"Gemini generation error: {exc}") from exc

        raise AIUnavailableError("Exhausted retries connecting to Google Gemini.")

    @classmethod
    def is_available(cls) -> bool:
        key = get_gemini_api_key()
        cfg = load_ai_config()
        return bool(key and cfg.get("gemini_consent_given", False))

    @classmethod
    def get_active_model(cls) -> str:
        cfg = load_ai_config()
        return cfg.get("gemini_model") or "gemini-3.8-flash"


def get_provider(provider_type: AIProviderType | str | None = None) -> type[OllamaProvider] | type[GeminiProvider]:
    """Retrieve the provider class for the given or active provider type."""
    prov = AIProviderType(provider_type) if provider_type else get_active_provider()
    if prov == AIProviderType.GEMINI:
        return GeminiProvider
    return OllamaProvider


# ─── Unified High-Level Gateway Functions ──────────────────────────────────────

_active_model: str | None = None


def get_selected_model() -> str | None:
    global _active_model
    if _active_model:
        return _active_model
    cfg = load_ai_config()
    return cfg.get("selected_model") or get_settings().default_ai_model


def set_selected_model(model_name: str | None) -> None:
    global _active_model
    _active_model = model_name
    if model_name:
        cfg = load_ai_config()
        cfg["selected_model"] = model_name
        save_ai_config(cfg)


def get_active_provider() -> AIProviderType:
    cfg = load_ai_config()
    p = cfg.get("active_provider", AIProviderType.OLLAMA.value)
    try:
        return AIProviderType(p)
    except ValueError:
        return AIProviderType.OLLAMA


def set_active_provider(provider: str | AIProviderType) -> None:
    prov_str = provider.value if isinstance(provider, AIProviderType) else str(provider)
    cfg = load_ai_config()
    cfg["active_provider"] = prov_str
    save_ai_config(cfg)


def get_ai_status() -> dict[str, Any]:
    """Return unified status across configured providers."""
    cfg = load_ai_config()
    active_prov = get_active_provider()
    ollama_health = OllamaProvider.check_health()
    gemini_health = GeminiProvider.check_health()

    return {
        "active_provider": active_prov.value,
        "selected_model": get_selected_model() if active_prov == AIProviderType.OLLAMA else cfg.get("gemini_model"),
        "fallback_policy": cfg.get("fallback_policy", "deterministic"),
        "consent_granted": cfg.get("gemini_consent_given", False),
        "gemini_consent_given": cfg.get("gemini_consent_given", False),
        "gemini_configured": bool(get_gemini_api_key()),
        "gemini_key_configured": bool(get_gemini_api_key()),
        "gemini_key_hint": gemini_health.get("key_hint"),
        "gemini_key_masked": gemini_health.get("key_hint"),
        "ollama": ollama_health,
        "gemini": gemini_health,
        # Legacy fields for backward compatibility
        "provider": active_prov.value,
        "url": ollama_health["url"],
        "status": ollama_health["status"] if active_prov == AIProviderType.OLLAMA else gemini_health["status"],
        "models": ollama_health["models"],
        "selected_model_available": ollama_health["selected_model_available"],
        "error": ollama_health["error"] if active_prov == AIProviderType.OLLAMA else gemini_health["error"],
    }


def get_providers_list() -> list[dict[str, Any]]:
    """Return the list of all supported AI providers."""
    ollama_info = OllamaProvider.check_health()
    gemini_info = GeminiProvider.check_health()
    active_prov = get_active_provider()

    return [
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "status": "available" if ollama_info["status"] == "connected" else ollama_info["status"],
            "enabled": True,
            "is_local": True,
            "is_active": active_prov == AIProviderType.OLLAMA,
            "endpoint": ollama_info["url"],
            "models_count": len(ollama_info["models"]),
            "description": "100% private, runs on your device, zero fees or API keys.",
        },
        {
            "id": "gemini",
            "name": "Google Gemini (Cloud)",
            "status": gemini_info["status"],
            "enabled": True,
            "is_local": False,
            "is_active": active_prov == AIProviderType.GEMINI,
            "endpoint": "https://generativelanguage.googleapis.com",
            "models_count": len(gemini_info["models"]),
            "key_hint": gemini_info["key_hint"],
            "consent_given": gemini_info["consent_given"],
            "description": "High reasoning fidelity, requires free Google API key & internet connection.",
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "status": "coming_soon",
            "enabled": False,
            "is_local": False,
            "is_active": False,
            "models_count": 0,
            "description": "Commercial cloud provider (Coming soon).",
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "status": "coming_soon",
            "enabled": False,
            "is_local": False,
            "is_active": False,
            "models_count": 0,
            "description": "Commercial cloud provider (Coming soon).",
        },
    ]


def generate_completion(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: float = 45.0,
    provider: AIProviderType | str | None = None,
    redact_pii: bool = True,
    response_json: bool = False,
) -> str:
    """
    Unified text generation entry point.
    Routes to the active provider (or explicit override).
    Applies privacy redaction when appropriate.
    Strictly follows fallback policy without silent leakage.
    """
    active_prov = (
        AIProviderType(provider)
        if provider
        else get_active_provider()
    )

    clean_prompt = redact_personal_identifiers(prompt) if (redact_pii and active_prov == AIProviderType.GEMINI) else prompt
    clean_system = redact_personal_identifiers(system_prompt) if (redact_pii and system_prompt and active_prov == AIProviderType.GEMINI) else system_prompt

    if active_prov == AIProviderType.GEMINI:
        return GeminiProvider.generate(
            prompt=clean_prompt,
            system_prompt=clean_system,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_json=response_json,
        )

    # Default: Ollama
    return OllamaProvider.generate(
        prompt=clean_prompt,
        system_prompt=clean_system,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        response_json=response_json,
    )


def generate_structured(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.1,
    timeout_seconds: float = 45.0,
    provider: AIProviderType | str | None = None,
    redact_pii: bool = True,
) -> dict[str, Any]:
    """
    Generate structured JSON output from the active provider.
    Validates JSON decodability and handles retries.
    """
    raw = generate_completion(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        provider=provider,
        redact_pii=redact_pii,
        response_json=True,
    )

    # Attempt direct JSON parsing
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Heuristic extraction of ```json ... ``` code fence if present
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        # Find first { and last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start : end + 1])
        raise AIGatewayError(f"Model did not return valid JSON output: {raw[:200]}")
