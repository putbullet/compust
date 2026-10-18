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

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..config import get_settings
from ..logging import get_logger
from ..paths import get_user_data_dir

logger = get_logger(__name__)


# ─── Enums & Exceptions ─────────────────────────────────────────────────────────

class AIProviderType(str, Enum):
    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENAI = "openai"


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
    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


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
        "gemini_model": "gemini-2.5-flash",
        "gemini_consent_given": False,
        "openai_model": "gpt-4o-mini",
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


def resolve_effective_user_id(db: Session, user_id: int | None = None) -> int:
    """Resolve target user_id, falling back to first active user or creating local default."""
    if user_id is not None:
        return user_id
    from ..models import User
    first_user = db.query(User).filter(User.is_active == True).first()
    if first_user:
        return first_user.id
    any_user = db.query(User).first()
    if any_user:
        return any_user.id
    # Create local default user if DB is brand new
    default_user = User(
        id=1,
        email="local@compust.internal",
        password_hash="",
        first_name="Local",
        last_name="User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(default_user)
    db.commit()
    return default_user.id


def get_or_create_user_ai_config(db: Session, user_id: int | None = None) -> Any:
    """Retrieve the persistent user AI configuration row from the database, creating if missing."""
    from ..models import UserAIConfig
    eff_user_id = resolve_effective_user_id(db, user_id)
    row = db.query(UserAIConfig).filter(UserAIConfig.user_id == eff_user_id).first()
    if row:
        return row

    # Seed from ai_config.json if available
    file_cfg = load_ai_config()
    row = UserAIConfig(
        user_id=eff_user_id,
        active_provider=file_cfg.get("active_provider", AIProviderType.OLLAMA.value),
        selected_model=file_cfg.get("selected_model", "qwen3.5:0.8b"),
        gemini_model=file_cfg.get("gemini_model", "gemini-2.5-flash"),
        openai_model=file_cfg.get("openai_model", "gpt-4o-mini"),
        consent_granted=file_cfg.get("gemini_consent_given", file_cfg.get("consent_granted", False)),
        gemini_api_key_encrypted=file_cfg.get("gemini_api_key_encrypted"),
        openai_api_key_encrypted=file_cfg.get("openai_api_key_encrypted"),
        fallback_policy=file_cfg.get("fallback_policy", "deterministic"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def sync_user_ai_config_on_startup() -> None:
    """Ensure active database user has an initialized UserAIConfig row synced with existing credentials."""
    try:
        from ..database import SessionLocal
        with SessionLocal() as db:
            get_or_create_user_ai_config(db, None)
    except Exception as e:
        logger.debug(f"sync_user_ai_config_on_startup non-fatal note: {e}")


def save_user_ai_settings(
    db: Session,
    user_id: int | None,
    updates: dict[str, Any],
) -> Any:
    """Persist all AI configuration updates directly to the database record and sync file mirror."""
    row = get_or_create_user_ai_config(db, user_id)

    if "active_provider" in updates and updates["active_provider"]:
        row.active_provider = str(updates["active_provider"])
    if "selected_model" in updates and updates["selected_model"]:
        row.selected_model = str(updates["selected_model"])
    if "gemini_model" in updates and updates["gemini_model"]:
        row.gemini_model = str(updates["gemini_model"])
    if "openai_model" in updates and updates["openai_model"]:
        row.openai_model = str(updates["openai_model"])
    if "consent_granted" in updates and updates["consent_granted"] is not None:
        row.consent_granted = bool(updates["consent_granted"])
    if "gemini_consent_given" in updates and updates["gemini_consent_given"] is not None:
        row.consent_granted = bool(updates["gemini_consent_given"])
    if "fallback_policy" in updates and updates["fallback_policy"]:
        row.fallback_policy = str(updates["fallback_policy"])
    if "gemini_api_key_encrypted" in updates:
        row.gemini_api_key_encrypted = updates["gemini_api_key_encrypted"]
    if "openai_api_key_encrypted" in updates:
        row.openai_api_key_encrypted = updates["openai_api_key_encrypted"]

    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    # Mirror to file cache for fallback
    cfg = load_ai_config()
    if row.active_provider:
        cfg["active_provider"] = row.active_provider
    if row.selected_model:
        cfg["selected_model"] = row.selected_model
    if row.gemini_model:
        cfg["gemini_model"] = row.gemini_model
    if row.openai_model:
        cfg["openai_model"] = row.openai_model
    cfg["gemini_consent_given"] = row.consent_granted
    cfg["consent_granted"] = row.consent_granted
    if row.fallback_policy:
        cfg["fallback_policy"] = row.fallback_policy
    if row.gemini_api_key_encrypted:
        cfg["gemini_api_key_encrypted"] = row.gemini_api_key_encrypted
    if row.openai_api_key_encrypted:
        cfg["openai_api_key_encrypted"] = row.openai_api_key_encrypted
    save_ai_config(cfg)

    return row


def get_gemini_api_key(db: Session | None = None, user_id: int | None = None) -> str | None:
    """
    Retrieve Google Gemini API key from:
    1. Database record (UserAIConfig.gemini_api_key_encrypted)
    2. Local persistent user configuration file (DPAPI encrypted)
    3. Plain text key in config
    4. Environment variable GEMINI_API_KEY
    5. Untracked local .env file
    """
    # 1. Database record
    cfg_row = None
    if db is not None:
        try:
            cfg_row = get_or_create_user_ai_config(db, user_id)
        except Exception:
            pass
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                cfg_row = get_or_create_user_ai_config(session, user_id)
        except Exception:
            pass

    if cfg_row and cfg_row.gemini_api_key_encrypted:
        dec = _dpapi_decrypt(cfg_row.gemini_api_key_encrypted)
        if dec:
            return dec

    # 2. DPAPI encrypted key in config
    cfg = load_ai_config()
    enc_key = (cfg.get("gemini_api_key_encrypted") or "").strip()
    if enc_key:
        dec = _dpapi_decrypt(enc_key)
        if dec:
            return dec

    # 3. Plain text key in config (legacy or non-Windows)
    cfg_key = (cfg.get("gemini_api_key") or "").strip()
    if cfg_key:
        return cfg_key

    # 4. Environment variable
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    # 5. Untracked local .env file
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


def set_gemini_api_key(key: str | None, db: Session | None = None, user_id: int | None = None) -> None:
    """Store or clear the Gemini API key in DB and user configuration with DPAPI protection."""
    enc = _dpapi_encrypt(key.strip()) if (key and key.strip()) else None

    # Update in DB
    if db is not None:
        try:
            row = get_or_create_user_ai_config(db, user_id)
            row.gemini_api_key_encrypted = enc
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save gemini key in DB: {e}")
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                row = get_or_create_user_ai_config(session, user_id)
                row.gemini_api_key_encrypted = enc
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save gemini key in DB: {e}")

    # Mirror to file config
    cfg = load_ai_config()
    if enc:
        if enc.startswith("dpapi:"):
            cfg["gemini_api_key_encrypted"] = enc
            cfg.pop("gemini_api_key", None)
        else:
            cfg["gemini_api_key"] = key.strip() if key else ""
    else:
        cfg.pop("gemini_api_key", None)
        cfg.pop("gemini_api_key_encrypted", None)
    save_ai_config(cfg)


def get_openai_api_key(db: Session | None = None, user_id: int | None = None) -> str | None:
    """
    Retrieve OpenAI API key from:
    1. Database record (UserAIConfig.openai_api_key_encrypted)
    2. Local persistent user configuration file
    3. Plain text key in config
    4. Environment variable OPENAI_API_KEY
    5. Untracked local .env file
    """
    cfg_row = None
    if db is not None:
        try:
            cfg_row = get_or_create_user_ai_config(db, user_id)
        except Exception:
            pass
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                cfg_row = get_or_create_user_ai_config(session, user_id)
        except Exception:
            pass

    if cfg_row and cfg_row.openai_api_key_encrypted:
        dec = _dpapi_decrypt(cfg_row.openai_api_key_encrypted)
        if dec:
            return dec

    cfg = load_ai_config()
    enc_key = (cfg.get("openai_api_key_encrypted") or "").strip()
    if enc_key:
        dec = _dpapi_decrypt(enc_key)
        if dec:
            return dec

    cfg_key = (cfg.get("openai_api_key") or "").strip()
    if cfg_key:
        return cfg_key

    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    for candidate in [Path(".env"), Path(__file__).resolve().parents[3] / ".env"]:
        try:
            if candidate.is_file():
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass

    return None


def set_openai_api_key(key: str | None, db: Session | None = None, user_id: int | None = None) -> None:
    """Store or clear the OpenAI API key in DB and user configuration with DPAPI protection."""
    enc = _dpapi_encrypt(key.strip()) if (key and key.strip()) else None

    # Update in DB
    if db is not None:
        try:
            row = get_or_create_user_ai_config(db, user_id)
            row.openai_api_key_encrypted = enc
            row.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save openai key in DB: {e}")
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                row = get_or_create_user_ai_config(session, user_id)
                row.openai_api_key_encrypted = enc
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save openai key in DB: {e}")

    cfg = load_ai_config()
    if enc:
        if enc.startswith("dpapi:"):
            cfg["openai_api_key_encrypted"] = enc
            cfg.pop("openai_api_key", None)
        else:
            cfg["openai_api_key"] = key.strip() if key else ""
    else:
        cfg.pop("openai_api_key", None)
        cfg.pop("openai_api_key_encrypted", None)
    save_ai_config(cfg)


# ─── Provider Implementations ──────────────────────────────────────────────────

class OllamaProvider:
    """Local, offline Ollama provider."""

    @staticmethod
    def get_url() -> str:
        env_url = os.environ.get("OLLAMA_BASE_URL")
        if env_url:
            return env_url.rstrip("/")
        settings = get_settings()
        return settings.ollama_url.rstrip("/")

    @classmethod
    def check_health(cls, url: str | None = None, db: Session | None = None, user_id: int | None = None) -> dict[str, Any]:
        target_url = (url or cls.get_url()).rstrip("/")
        selected_ollama = get_selected_model(AIProviderType.OLLAMA, db=db, user_id=user_id)
        status_data: dict[str, Any] = {
            "provider": "ollama",
            "name": "Ollama (Local)",
            "url": target_url,
            "status": "unavailable",
            "models": [],
            "selected_model": selected_ollama,
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
                    current_selected = selected_ollama or (installed_names[0] if installed_names else None)

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
    def is_available(cls, db: Session | None = None, user_id: int | None = None) -> bool:
        health = cls.check_health(db=db, user_id=user_id)
        return health.get("status") == "connected" and bool(health.get("models"))

    @classmethod
    def get_active_model(cls, db: Session | None = None, user_id: int | None = None) -> str:
        return get_selected_model(AIProviderType.OLLAMA, db=db, user_id=user_id) or "qwen3.5:0.8b"


class GeminiProvider:
    """Google Gemini Cloud AI Provider using direct HTTPS REST API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    @classmethod
    def get_base_url(cls) -> str:
        return os.environ.get("GEMINI_BASE_URL", cls.BASE_URL).rstrip("/")

    # Verified real Google Gemini API model IDs (as of Oct 2026).
    # These are shown only when no API key is configured yet.
    # When a key is present, the live /v1beta/models endpoint is queried instead.
    FALLBACK_MODELS = [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Recommended)", "recommended": True},
        {"id": "gemini-2.5-flash-latest", "name": "Gemini 2.5 Flash Latest", "recommended": False},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (Deep Reasoning)", "recommended": False},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "recommended": False},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "recommended": False},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "recommended": False},
    ]

    @classmethod
    def get_available_models(cls, api_key: str | None = None) -> list[dict[str, Any]]:
        key = api_key or get_gemini_api_key()
        if not key:
            return cls.FALLBACK_MODELS
        try:
            with httpx.Client(timeout=6.0) as client:
                resp = client.get(
                    f"{cls.get_base_url()}/models",
                    headers={"x-goog-api-key": key},
                )
                if resp.status_code == 200:
                    raw_models = resp.json().get("models", [])
                    models_list: list[dict[str, Any]] = []
                    for m in raw_models:
                        methods = m.get("supportedGenerationMethods", [])
                        m_name = m.get("name", "")
                        if "generateContent" in methods and (m_name.startswith("models/gemini") or m_name.startswith("models/gemma")):
                            if any(x in m_name for x in ["tts", "image", "robotics", "computer-use", "clip"]):
                                continue
                            model_id = m_name.removeprefix("models/")
                            display = m.get("displayName") or model_id
                            desc = m.get("description", "")
                            is_rec = "2.5-flash" in model_id
                            models_list.append({
                                "id": model_id,
                                "name": f"{display}{' (Recommended)' if is_rec else ''}",
                                "description": desc[:100] if desc else None,
                                "recommended": is_rec,
                            })
                    if models_list:
                        models_list.sort(key=lambda x: (not x.get("recommended", False), x["id"]))
                        return models_list
        except Exception as exc:
            logger.debug(f"Could not dynamically query Gemini models: {exc}")
        return cls.FALLBACK_MODELS

    @classmethod
    def test_connection(cls, api_key: str | None = None, model: str | None = None, db: Session | None = None, user_id: int | None = None) -> dict[str, Any]:
        key = api_key or get_gemini_api_key(db=db, user_id=user_id)
        cfg = load_ai_config()
        target_model = model or get_selected_model(AIProviderType.GEMINI, db=db, user_id=user_id) or cfg.get("gemini_model") or "gemini-2.5-flash"
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
                url = f"{cls.get_base_url()}/models/{target_model}:generateContent"
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
                        "message": f"Model '{target_model}' not found or deprecated by Google. Try 'gemini-2.5-flash'.",
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
    def check_health(cls, api_key: str | None = None, db: Session | None = None, user_id: int | None = None) -> dict[str, Any]:
        key = api_key or get_gemini_api_key(db=db, user_id=user_id)
        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass

        cfg = load_ai_config()
        gemini_model = (row.gemini_model if row and row.gemini_model else None) or cfg.get("gemini_model", "gemini-2.5-flash")
        file_consent = bool(cfg.get("gemini_consent_given", cfg.get("consent_granted", False)))
        consent_given = (bool(row.consent_granted) if row else True) and file_consent

        status_data: dict[str, Any] = {
            "provider": "gemini",
            "name": "Google Gemini (Cloud)",
            "status": "not_configured" if not key else "configured",
            "models": cls.get_available_models(key),
            "selected_model": gemini_model,
            "key_hint": mask_api_key(key),
            "consent_given": consent_given,
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
                    f"{cls.get_base_url()}/models",
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
        db: Session | None = None,
        user_id: int | None = None,
    ) -> str:
        key = get_gemini_api_key(db=db, user_id=user_id)
        if not key:
            raise AIAuthenticationError("Google Gemini API key not configured. Add a key in AI Settings.")

        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass

        cfg = load_ai_config()
        file_consent = bool(cfg.get("gemini_consent_given", cfg.get("consent_granted", False)))
        consent_given = (bool(row.consent_granted) if row else True) and file_consent
        if not consent_given:
            raise AIConsentRequiredError(
                "Cloud processing consent required before sending queries to Google Gemini. "
                "Enable consent in AI Settings."
            )

        target_model = model or (row.gemini_model if row and row.gemini_model else None) or cfg.get("gemini_model") or "gemini-2.5-flash"
        url = f"{cls.get_base_url()}/models/{target_model}:generateContent"

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
                    retry_after_sec: float | None = None
                    retry_str = None
                    try:
                        err_json = resp.json()
                        err_data = err_json.get("error", {})
                        for detail in err_data.get("details", []):
                            if detail.get("@type", "").endswith("RetryInfo"):
                                raw_delay = detail.get("retryDelay")
                                if raw_delay and isinstance(raw_delay, str):
                                    retry_after_sec = float(raw_delay.rstrip("s"))
                        if retry_after_sec is None:
                            raw_msg = err_data.get("message", "")
                            match = re.search(r"retry in (\d+(?:\.\d+)?)(s|m|h)", raw_msg)
                            if match:
                                val = float(match.group(1))
                                unit = match.group(2)
                                if unit == "s":
                                    retry_after_sec = val
                                elif unit == "m":
                                    retry_after_sec = val * 60
                                elif unit == "h":
                                    retry_after_sec = val * 3600
                    except Exception:
                        pass

                    if retry_after_sec is None:
                        headers_obj = getattr(resp, "headers", None)
                        if headers_obj and hasattr(headers_obj, "get"):
                            header_retry = headers_obj.get("retry-after")
                            if header_retry:
                                try:
                                    retry_after_sec = float(header_retry)
                                except ValueError:
                                    pass

                    if retry_after_sec is not None and retry_after_sec > 0:
                        if retry_after_sec < 60:
                            retry_str = f"~{int(retry_after_sec)}s"
                        elif retry_after_sec < 3600:
                            mins = int(retry_after_sec // 60)
                            secs = int(retry_after_sec % 60)
                            retry_str = f"~{mins}m {secs}s" if secs else f"~{mins}m"
                        else:
                            hours = int(retry_after_sec // 3600)
                            mins = int((retry_after_sec % 3600) // 60)
                            retry_str = f"~{hours}h {mins}m"
                        msg = f"Rate limited by Google Gemini's free tier — try again in {retry_str}."
                    else:
                        msg = "Rate limited by Google Gemini's free tier. Please try again shortly."

                    logger.warning(f"Gemini 429 rate limit hit: {msg} (retry_after_sec={retry_after_sec})")
                    # Zero retries on 429 — immediately raise to preserve user quota
                    raise AIRateLimitError(msg, retry_after_seconds=retry_after_sec) from None

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
    def is_available(cls, db: Session | None = None, user_id: int | None = None) -> bool:
        key = get_gemini_api_key(db=db, user_id=user_id)
        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass
        cfg = load_ai_config()
        file_consent = bool(cfg.get("gemini_consent_given", cfg.get("consent_granted", False)))
        consent = (bool(row.consent_granted) if row else True) and file_consent
        return bool(key and consent)

    @classmethod
    def get_active_model(cls, db: Session | None = None, user_id: int | None = None) -> str:
        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass
        return (row.gemini_model if row and row.gemini_model else None) or load_ai_config().get("gemini_model") or "gemini-2.5-flash"


class OpenAIProvider:
    """OpenAI Cloud AI Provider using direct HTTPS REST API."""

    BASE_URL = "https://api.openai.com/v1"

    @classmethod
    def get_base_url(cls) -> str:
        return os.environ.get("OPENAI_BASE_URL", cls.BASE_URL).rstrip("/")

    # Verified OpenAI chat-completion models (as of Oct 2026).
    # Shown only when no API key is configured; live list is fetched from /v1/models when key is set.
    FALLBACK_MODELS = [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Recommended)", "recommended": True, "description": "Fast, highly capable, and cost-effective"},
        {"id": "gpt-4o", "name": "GPT-4o", "recommended": False, "description": "Flagship high-intelligence multimodal model"},
        {"id": "gpt-4.1", "name": "GPT-4.1", "recommended": False, "description": "Latest GPT-4 flagship with enhanced instruction following"},
        {"id": "gpt-4.1-mini", "name": "GPT-4.1 Mini", "recommended": False, "description": "Smaller, faster GPT-4.1 for latency-sensitive tasks"},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "recommended": False, "description": "High capability with large context window"},
        {"id": "o4-mini", "name": "o4-mini", "recommended": False, "description": "Fast reasoning model for complex logic and math"},
        {"id": "o3-mini", "name": "o3-mini", "recommended": False, "description": "Reasoning model for complex logic and math"},
    ]

    @classmethod
    def get_available_models(cls, api_key: str | None = None) -> list[dict[str, Any]]:
        key = api_key or get_openai_api_key()
        if not key:
            return cls.FALLBACK_MODELS
        try:
            with httpx.Client(timeout=6.0) as client:
                resp = client.get(
                    f"{cls.get_base_url()}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    raw_models = resp.json().get("data", [])
                    models_list: list[dict[str, Any]] = []
                    allowed_prefixes = ("gpt-4", "gpt-3.5", "o1", "o3", "o4", "chatgpt")
                    for m in raw_models:
                        model_id = m.get("id", "")
                        if any(model_id.startswith(p) for p in allowed_prefixes):
                            if any(sub in model_id for sub in ["realtime", "audio", "transcription", "tts", "moderation", "embedding", "instruct", "vision", "preview"]):
                                continue
                            is_rec = model_id == "gpt-4o-mini"
                            models_list.append({
                                "id": model_id,
                                "name": f"{model_id}{' (Recommended)' if is_rec else ''}",
                                "recommended": is_rec,
                            })
                    if models_list:
                        models_list.sort(key=lambda x: (not x.get("recommended", False), x["id"]))
                        return models_list
        except Exception as exc:
            logger.debug(f"Could not dynamically query OpenAI models: {exc}")
        return cls.FALLBACK_MODELS

    @classmethod
    def test_connection(cls, api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
        key = api_key or get_openai_api_key()
        cfg = load_ai_config()
        target_model = model or cfg.get("openai_model") or "gpt-4o-mini"
        if not key:
            return {
                "success": False,
                "provider": "openai",
                "model": target_model,
                "message": "No OpenAI API key provided. Please enter an API key.",
                "latency_ms": None,
            }
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0) as client:
                url = f"{cls.get_base_url()}/chat/completions"
                payload = {
                    "model": target_model,
                    "messages": [{"role": "user", "content": "Ping"}],
                    "max_tokens": 5,
                }
                resp = client.post(
                    url,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=payload,
                )
                latency = int((time.perf_counter() - t0) * 1000)
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "provider": "openai",
                        "model": target_model,
                        "message": f"Successfully connected to OpenAI ({target_model}) in {latency}ms.",
                        "latency_ms": latency,
                    }
                if resp.status_code in (401, 403):
                    return {
                        "success": False,
                        "provider": "openai",
                        "model": target_model,
                        "message": "Invalid OpenAI API key. Please check your credentials.",
                        "latency_ms": latency,
                    }
                if resp.status_code == 429:
                    return {
                        "success": False,
                        "provider": "openai",
                        "model": target_model,
                        "message": "OpenAI quota or rate limit exceeded. Please check your account usage.",
                        "latency_ms": latency,
                    }
                if resp.status_code == 404:
                    return {
                        "success": False,
                        "provider": "openai",
                        "model": target_model,
                        "message": f"Model '{target_model}' not found on OpenAI. Try 'gpt-4o-mini'.",
                        "latency_ms": latency,
                    }
                return {
                    "success": False,
                    "provider": "openai",
                    "model": target_model,
                    "message": f"OpenAI returned HTTP {resp.status_code}: {resp.text[:120]}",
                    "latency_ms": latency,
                }
        except httpx.ConnectError:
            return {
                "success": False,
                "provider": "openai",
                "model": target_model,
                "message": "Cannot reach OpenAI. Please check your internet connection.",
                "latency_ms": None,
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "provider": "openai",
                "model": target_model,
                "message": "Connection to OpenAI timed out (10s limit).",
                "latency_ms": None,
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "openai",
                "model": target_model,
                "message": f"Connection test failed: {str(e)}",
                "latency_ms": None,
            }

    @classmethod
    def check_health(cls, api_key: str | None = None, db: Session | None = None, user_id: int | None = None) -> dict[str, Any]:
        key = api_key or get_openai_api_key(db=db, user_id=user_id)
        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass

        cfg = load_ai_config()
        openai_model = (row.openai_model if row and row.openai_model else None) or cfg.get("openai_model", "gpt-4o-mini")

        status_data: dict[str, Any] = {
            "provider": "openai",
            "name": "OpenAI (Cloud)",
            "status": "not_configured" if not key else "configured",
            "models": cls.get_available_models(key),
            "selected_model": openai_model,
            "key_hint": mask_api_key(key),
            "error": None,
            "is_local": False,
        }

        if not key:
            status_data["status"] = "not_configured"
            status_data["error"] = "No OpenAI API key configured. Enter an API key in Settings."
            return status_data

        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    f"{cls.get_base_url()}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if resp.status_code == 200:
                    status_data["status"] = "connected"
                elif resp.status_code in (401, 403):
                    status_data["status"] = "invalid_key"
                    status_data["error"] = "Invalid OpenAI API key. Please check your credentials."
                elif resp.status_code == 429:
                    status_data["status"] = "rate_limited"
                    status_data["error"] = "OpenAI API rate limit or quota exceeded."
                else:
                    status_data["status"] = "error"
                    status_data["error"] = f"HTTP {resp.status_code}: {resp.text}"
        except httpx.ConnectError:
            status_data["status"] = "network_error"
            status_data["error"] = "Cannot reach OpenAI API. Check your internet connection."
        except httpx.TimeoutException:
            status_data["status"] = "timeout"
            status_data["error"] = "Connection to OpenAI API timed out."
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
        db: Session | None = None,
        user_id: int | None = None,
    ) -> str:
        key = get_openai_api_key(db=db, user_id=user_id)
        if not key:
            raise AIAuthenticationError("OpenAI API key not configured. Add a key in AI Settings.")

        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass

        cfg = load_ai_config()
        target_model = model or (row.openai_model if row and row.openai_model else None) or cfg.get("openai_model") or "gpt-4o-mini"
        url = f"{cls.get_base_url()}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
        }
        if not (target_model.startswith("o1") or target_model.startswith("o3")):
            payload["temperature"] = temperature
            payload["max_tokens"] = 4096
        else:
            payload["max_completion_tokens"] = 4096

        if response_json:
            payload["response_format"] = {"type": "json_object"}

        max_attempts = 3
        backoff_delays = [1.0, 2.0, 4.0]

        for attempt in range(max_attempts):
            try:
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise AIGatewayError("OpenAI returned an empty choice list.")
                    message = choices[0].get("message", {})
                    return (message.get("content") or "").strip()

                if resp.status_code in (401, 403):
                    raise AIAuthenticationError("Invalid or unauthorized OpenAI API key.")

                if resp.status_code == 429:
                    if attempt < max_attempts - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise AIRateLimitError("OpenAI quota or rate limit exceeded. Please check usage and try again.")

                if resp.status_code in (500, 502, 503, 504):
                    if attempt < max_attempts - 1:
                        time.sleep(backoff_delays[attempt])
                        continue
                    raise AIUnavailableError(f"OpenAI service unavailable (HTTP {resp.status_code}).")

                raise AIGatewayError(f"OpenAI returned HTTP {resp.status_code}: {resp.text}")

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < max_attempts - 1:
                    time.sleep(backoff_delays[attempt])
                    continue
                raise AIUnavailableError(f"Connection to OpenAI failed: {exc}") from exc
            except (AIGatewayError, AIAuthenticationError, AIRateLimitError, AISafetyBlockError, AIConsentRequiredError):
                raise
            except Exception as exc:
                raise AIGatewayError(f"OpenAI generation error: {exc}") from exc

        raise AIUnavailableError("Exhausted retries connecting to OpenAI.")

    @classmethod
    def is_available(cls, db: Session | None = None, user_id: int | None = None) -> bool:
        key = get_openai_api_key(db=db, user_id=user_id)
        return bool(key)

    @classmethod
    def get_active_model(cls, db: Session | None = None, user_id: int | None = None) -> str:
        row = None
        if db is not None:
            try:
                row = get_or_create_user_ai_config(db, user_id)
            except Exception:
                pass
        else:
            try:
                from ..database import SessionLocal
                with SessionLocal() as session:
                    row = get_or_create_user_ai_config(session, user_id)
            except Exception:
                pass
        return (row.openai_model if row and row.openai_model else None) or load_ai_config().get("openai_model") or "gpt-4o-mini"


def get_provider(
    provider_type: AIProviderType | str | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> type[OllamaProvider] | type[GeminiProvider] | type[OpenAIProvider]:
    """Retrieve the provider class for the given or active provider type."""
    prov = AIProviderType(provider_type) if provider_type else get_active_provider(db=db, user_id=user_id)
    if prov == AIProviderType.GEMINI:
        return GeminiProvider
    if prov == AIProviderType.OPENAI:
        return OpenAIProvider
    return OllamaProvider


def is_ai_available(
    provider_type: AIProviderType | str | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> bool:
    """Check if the active (or specified) provider is configured and available."""
    provider_cls = get_provider(provider_type, db=db, user_id=user_id)
    return provider_cls.is_available(db=db, user_id=user_id)


# ─── Unified High-Level Gateway Functions ──────────────────────────────────────


def get_selected_model(
    provider_type: AIProviderType | str | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> str | None:
    row = None
    if db is not None:
        try:
            row = get_or_create_user_ai_config(db, user_id)
        except Exception:
            pass
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                row = get_or_create_user_ai_config(session, user_id)
        except Exception:
            pass

    prov = AIProviderType(provider_type) if provider_type else get_active_provider(db=db, user_id=user_id)
    cfg = load_ai_config()
    if prov == AIProviderType.GEMINI:
        return (row.gemini_model if row and row.gemini_model else None) or cfg.get("gemini_model") or "gemini-2.5-flash"
    if prov == AIProviderType.OPENAI:
        return (row.openai_model if row and row.openai_model else None) or cfg.get("openai_model") or "gpt-4o-mini"
    return (row.selected_model if row and row.selected_model else None) or cfg.get("selected_model") or get_settings().default_ai_model


def set_selected_model(
    model_name: str | None,
    provider_type: AIProviderType | str | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> None:
    if not model_name:
        return
    prov = AIProviderType(provider_type) if provider_type else get_active_provider(db=db, user_id=user_id)
    updates: dict[str, Any] = {}
    if prov == AIProviderType.GEMINI:
        updates["gemini_model"] = model_name
    elif prov == AIProviderType.OPENAI:
        updates["openai_model"] = model_name
    else:
        updates["selected_model"] = model_name

    if db is not None:
        save_user_ai_settings(db, user_id, updates)
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                save_user_ai_settings(session, user_id, updates)
        except Exception as e:
            logger.error(f"Failed to save selected model in DB: {e}")


def get_active_provider(
    db: Session | None = None,
    user_id: int | None = None,
) -> AIProviderType:
    row = None
    if db is not None:
        try:
            row = get_or_create_user_ai_config(db, user_id)
        except Exception:
            pass
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                row = get_or_create_user_ai_config(session, user_id)
        except Exception:
            pass

    if row and row.active_provider:
        try:
            return AIProviderType(row.active_provider)
        except ValueError:
            pass

    cfg = load_ai_config()
    p = cfg.get("active_provider", AIProviderType.OLLAMA.value)
    try:
        return AIProviderType(p)
    except ValueError:
        return AIProviderType.OLLAMA


def set_active_provider(
    provider: str | AIProviderType,
    db: Session | None = None,
    user_id: int | None = None,
) -> None:
    prov_str = provider.value if isinstance(provider, AIProviderType) else str(provider)
    if db is not None:
        save_user_ai_settings(db, user_id, {"active_provider": prov_str})
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                save_user_ai_settings(session, user_id, {"active_provider": prov_str})
        except Exception as e:
            logger.error(f"Failed to set active provider in DB: {e}")


def get_ai_status(db: Session | None = None, user_id: int | None = None) -> dict[str, Any]:
    """Return unified status across configured providers directly from persistent user settings."""
    row = None
    if db is not None:
        try:
            row = get_or_create_user_ai_config(db, user_id)
        except Exception:
            pass
    else:
        try:
            from ..database import SessionLocal
            with SessionLocal() as session:
                row = get_or_create_user_ai_config(session, user_id)
        except Exception:
            pass

    cfg = load_ai_config()
    active_prov = get_active_provider(db=db, user_id=user_id)
    ollama_health = OllamaProvider.check_health(db=db, user_id=user_id)
    gemini_health = GeminiProvider.check_health(db=db, user_id=user_id)
    openai_health = OpenAIProvider.check_health(db=db, user_id=user_id)

    active_health = ollama_health
    if active_prov == AIProviderType.GEMINI:
        active_health = gemini_health
    elif active_prov == AIProviderType.OPENAI:
        active_health = openai_health

    gemini_key = get_gemini_api_key(db=db, user_id=user_id)
    openai_key = get_openai_api_key(db=db, user_id=user_id)
    file_consent = bool(cfg.get("gemini_consent_given", cfg.get("consent_granted", False)))
    consent = (bool(row.consent_granted) if row else True) and file_consent
    fallback_policy = row.fallback_policy if row else cfg.get("fallback_policy", "deterministic")
    gemini_model = (row.gemini_model if row and row.gemini_model else None) or cfg.get("gemini_model", "gemini-2.5-flash")
    openai_model = (row.openai_model if row and row.openai_model else None) or cfg.get("openai_model", "gpt-4o-mini")

    return {
        "active_provider": active_prov.value,
        "selected_model": get_selected_model(provider_type=active_prov, db=db, user_id=user_id),
        "fallback_policy": fallback_policy,
        "consent_granted": consent,
        "gemini_consent_given": consent,
        "gemini_configured": bool(gemini_key),
        "gemini_key_configured": bool(gemini_key),
        "gemini_key_hint": gemini_health.get("key_hint"),
        "gemini_key_masked": gemini_health.get("key_hint"),
        "gemini_model": gemini_model,
        "openai_configured": bool(openai_key),
        "openai_key_configured": bool(openai_key),
        "openai_key_hint": openai_health.get("key_hint"),
        "openai_key_masked": openai_health.get("key_hint"),
        "openai_model": openai_model,
        "ollama": ollama_health,
        "gemini": gemini_health,
        "openai": openai_health,
        # Legacy fields for backward compatibility, mapped to ACTIVE provider
        "provider": active_prov.value,
        "url": active_health.get("url") or (active_health.get("models") and "cloud" or ""),
        "status": active_health.get("status", "unavailable"),
        "models": active_health.get("models", []),
        "selected_model_available": active_health.get("selected_model_available", True),
        "error": active_health.get("error"),
    }


def get_providers_list(db: Session | None = None, user_id: int | None = None) -> list[dict[str, Any]]:
    """Return the list of all supported AI providers."""
    ollama_info = OllamaProvider.check_health(db=db, user_id=user_id)
    gemini_info = GeminiProvider.check_health(db=db, user_id=user_id)
    openai_info = OpenAIProvider.check_health(db=db, user_id=user_id)
    active_prov = get_active_provider(db=db, user_id=user_id)

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
            "name": "OpenAI (Cloud)",
            "status": openai_info["status"],
            "enabled": True,
            "is_local": False,
            "is_active": active_prov == AIProviderType.OPENAI,
            "endpoint": "https://api.openai.com/v1",
            "models_count": len(openai_info["models"]),
            "key_hint": openai_info["key_hint"],
            "description": "Industry-standard cloud intelligence (GPT-4o, GPT-4o mini, o3-mini).",
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


def test_provider_connection(
    provider: str,
    api_key: str | None = None,
    model: str | None = None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    Gateway abstraction for connection testing across providers.
    Ensures callers do not need to import provider classes directly.
    """
    prov_clean = (provider or "").lower().strip()
    if prov_clean == "gemini":
        return GeminiProvider.test_connection(api_key=api_key, model=model, db=db, user_id=user_id)
    elif prov_clean == "openai":
        return OpenAIProvider.test_connection(api_key=api_key, model=model, db=db, user_id=user_id)
    else:
        return OllamaProvider.test_connection(model=model)


def generate_completion(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: float = 45.0,
    provider: AIProviderType | str | None = None,
    redact_pii: bool = True,
    response_json: bool = False,
    db: Session | None = None,
    user_id: int | None = None,
) -> str:
    """
    Unified text generation entry point.
    Routes to the active provider from user persistent database settings.
    Applies privacy redaction when appropriate.
    Strictly follows fallback policy without silent leakage.
    """
    active_prov = (
        AIProviderType(provider)
        if provider
        else get_active_provider(db=db, user_id=user_id)
    )

    clean_prompt = redact_personal_identifiers(prompt) if (redact_pii and active_prov in (AIProviderType.GEMINI, AIProviderType.OPENAI)) else prompt
    clean_system = redact_personal_identifiers(system_prompt) if (redact_pii and system_prompt and active_prov in (AIProviderType.GEMINI, AIProviderType.OPENAI)) else system_prompt

    # Sanitize model if caller passed an incompatible model name for active provider
    effective_model = model
    if active_prov == AIProviderType.GEMINI:
        if not effective_model or ":" in effective_model or effective_model.startswith("gpt-") or effective_model.startswith("qwen") or effective_model.startswith("o1") or effective_model.startswith("o3") or effective_model.startswith("o4"):
            effective_model = GeminiProvider.get_active_model(db=db, user_id=user_id)
        logger.info(f"AI Gateway routing request to Gemini (model={effective_model})")
        return GeminiProvider.generate(
            prompt=clean_prompt,
            system_prompt=clean_system,
            model=effective_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_json=response_json,
            db=db,
            user_id=user_id,
        )

    if active_prov == AIProviderType.OPENAI:
        if not effective_model or ":" in effective_model or effective_model.startswith("gemini-") or effective_model.startswith("qwen"):
            effective_model = OpenAIProvider.get_active_model(db=db, user_id=user_id)
        logger.info(f"AI Gateway routing request to OpenAI (model={effective_model})")
        return OpenAIProvider.generate(
            prompt=clean_prompt,
            system_prompt=clean_system,
            model=effective_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_json=response_json,
            db=db,
            user_id=user_id,
        )

    # Default: Ollama
    if effective_model and (effective_model.startswith("gemini-") or effective_model.startswith("gpt-") or effective_model.startswith("o1") or effective_model.startswith("o3")):
        effective_model = OllamaProvider.get_active_model(db=db, user_id=user_id)
    logger.info(f"AI Gateway routing request to Ollama (model={effective_model})")
    return OllamaProvider.generate(
        prompt=clean_prompt,
        system_prompt=clean_system,
        model=effective_model,
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
    db: Session | None = None,
    user_id: int | None = None,
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
        db=db,
        user_id=user_id,
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
