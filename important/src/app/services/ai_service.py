import httpx
from typing import Any
from ..config import get_settings
from ..logging import get_logger

logger = get_logger(__name__)

# In-memory selection cache, can also be initialized from config
_active_model: str | None = None


class OllamaError(Exception):
    pass


class OllamaUnavailableError(OllamaError):
    pass


def get_configured_ollama_url() -> str:
    settings = get_settings()
    return settings.ollama_url.rstrip("/")


def get_selected_model() -> str | None:
    global _active_model
    if _active_model:
        return _active_model
    settings = get_settings()
    return settings.default_ai_model


def set_selected_model(model_name: str | None) -> None:
    global _active_model
    _active_model = model_name


def check_ollama_runtime(url: str | None = None) -> dict[str, Any]:
    target_url = (url or get_configured_ollama_url()).rstrip("/")
    status_data: dict[str, Any] = {
        "provider": "ollama",
        "url": target_url,
        "status": "unavailable",
        "models": [],
        "selected_model": get_selected_model(),
        "selected_model_available": False,
        "error": None,
    }

    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{target_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("models", [])
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

                # Check selected model availability
                installed_names = [m["name"] for m in models_list]
                current_selected = get_selected_model()
                if not current_selected and installed_names:
                    # Auto-select the first installed model if none selected
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


def generate_completion(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    timeout_seconds: float = 45.0,
) -> str:
    url = get_configured_ollama_url()
    target_model = model or get_selected_model()

    if not target_model:
        # Check runtime to discover any available model
        status = check_ollama_runtime(url)
        if status["models"]:
            target_model = status["models"][0]["name"]
            set_selected_model(target_model)
        else:
            raise OllamaUnavailableError("No Ollama models installed or available.")

    payload: dict[str, Any] = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 2048,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(f"{url}/api/generate", json=payload)
            if resp.status_code == 200:
                result = resp.json()
                return result.get("response", "").strip()
            raise OllamaError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise OllamaUnavailableError(f"Cannot reach Ollama at {url}: {exc}") from exc
    except Exception as exc:
        raise OllamaError(f"Ollama generation failed: {exc}") from exc


def get_providers_list() -> list[dict[str, Any]]:
    runtime = check_ollama_runtime()
    return [
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "status": "available" if runtime["status"] == "connected" else runtime["status"],
            "enabled": True,
            "is_local": True,
            "endpoint": runtime["url"],
            "models_count": len(runtime["models"]),
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "status": "coming_soon",
            "enabled": False,
            "is_local": False,
            "endpoint": None,
            "models_count": 0,
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "status": "coming_soon",
            "enabled": False,
            "is_local": False,
            "endpoint": None,
            "models_count": 0,
        },
        {
            "id": "custom",
            "name": "Other Provider",
            "status": "coming_soon",
            "enabled": False,
            "is_local": False,
            "endpoint": None,
            "models_count": 0,
        },
    ]
