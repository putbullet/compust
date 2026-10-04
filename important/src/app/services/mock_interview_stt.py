"""
STT (Speech-to-Text) service for Mock Interview.

Primary engine: faster-whisper (local, CPU-capable, MIT license)
Audio is NEVER persisted after transcription — only the transcript text is kept.

Privacy posture:
- All processing is local (no audio leaves the device)
- Raw audio bytes are consumed in memory and discarded after transcription
- This is surfaced to the user on the pre-interview permission screen

Graceful degradation:
- If faster-whisper is not installed or model fails to load, returns a clear
  error message so the frontend can fall back to Web Speech API fallback
  (with explicit user disclosure that Web Speech API sends audio to the browser's
  cloud service — the user must opt in to that fallback explicitly)
"""

from __future__ import annotations

import logging
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any

from ..config import get_settings

logger = logging.getLogger("compust.mock_interview.stt")

# Lazy import — faster-whisper initialized on demand
_whisper_model = None
_whisper_available: Optional[bool] = None
_whisper_error_detail: Optional[str] = None


def _resolve_safe_cache_dirs() -> tuple[Path, Path]:
    """
    Dynamically resolve safe cache and temp directories on a drive with free space.
    Avoids [Errno 28] No space left on device when system drive (e.g. C:) is out of storage.
    """
    settings = get_settings()
    custom_cache = getattr(settings, "stt_cache_dir", None)
    if custom_cache:
        base = Path(custom_cache)
        hf_dir = base / "huggingface"
        tmp_dir = base / "temp"
        hf_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        return hf_dir, tmp_dir

    # Check candidate locations:
    # 1. Repo root .cache
    # 2. Path relative to current file
    repo_cache = Path(__file__).resolve().parent.parent.parent.parent / ".cache"
    for candidate in [repo_cache, Path("A:/code/compust/.cache")]:
        try:
            hf = candidate / "huggingface"
            tmp = candidate / "temp"
            hf.mkdir(parents=True, exist_ok=True)
            tmp.mkdir(parents=True, exist_ok=True)
            # Test write
            probe = tmp / ".probe_write"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return hf, tmp
        except Exception:
            continue

    # Fallback to standard system temp
    sys_temp = Path(tempfile.gettempdir())
    return sys_temp / "huggingface", sys_temp


def _get_whisper_model():
    global _whisper_model, _whisper_available, _whisper_error_detail

    if _whisper_model is not None:
        return _whisper_model

    settings = get_settings()
    model_size = getattr(settings, "stt_model", "tiny")
    device = getattr(settings, "stt_device", "cpu")
    compute_type = getattr(settings, "stt_compute_type", "int8")

    hf_cache, tmp_dir = _resolve_safe_cache_dirs()
    os.environ["HF_HOME"] = str(hf_cache)
    tempfile.tempdir = str(tmp_dir)

    try:
        from faster_whisper import WhisperModel
        logger.info(
            f"Loading faster-whisper model '{model_size}' (device={device}, "
            f"compute_type={compute_type}, download_root={hf_cache})..."
        )
        _whisper_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(hf_cache),
        )
        _whisper_available = True
        _whisper_error_detail = None
        logger.info(f"faster-whisper model '{model_size}' loaded successfully on {device}.")
        return _whisper_model
    except ImportError as e:
        _whisper_available = False
        _whisper_error_detail = f"faster-whisper package not installed or DLL missing: {e}"
        logger.warning(f"faster-whisper is not installed or import failed: {e}")
        return None
    except Exception as e:
        _whisper_available = False
        _whisper_error_detail = f"Failed to load faster-whisper model: {e}"
        logger.error(f"Failed to load faster-whisper model: {e}")
        return None


def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str = "audio/webm",
    language: str = "en",
) -> Dict[str, Any]:
    """
    Transcribe audio bytes using faster-whisper.

    audio_bytes: raw audio from MediaRecorder (typically audio/webm or audio/wav)
    Returns: {"transcript": str, "confidence": float|None, "engine": str, "error": str|None}

    PRIVACY NOTE:
    - audio_bytes are written to a temporary file, transcribed, then immediately deleted
    - No audio data is stored in the database or on disk after this function returns
    """
    result = {
        "transcript": "",
        "confidence": None,
        "engine": "faster-whisper",
        "duration_seconds": None,
        "error": None,
    }

    model = _get_whisper_model()
    if model is None:
        user_facing_err = (
            "Local speech recognition is currently unavailable. "
            "Please ensure faster-whisper is installed in your Python environment or switch to an available fallback."
        )
        if _whisper_error_detail:
            logger.warning(f"STT diagnostic detail: {_whisper_error_detail}")
        result["error"] = user_facing_err
        result["engine"] = "unavailable"
        return result

    if not audio_bytes or len(audio_bytes) < 100:
        result["error"] = "Audio clip too short or empty — no speech detected."
        return result

    # Write to safe temp file, transcribe, delete immediately
    _, tmp_dir = _resolve_safe_cache_dirs()
    suffix = _mime_to_suffix(mime_type)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, dir=str(tmp_dir), delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        segments, info = model.transcribe(
            tmp_path,
            language=language if language != "auto" else None,
            beam_size=2,
            vad_filter=True,             # Voice Activity Detection: skip silence
            vad_parameters=dict(min_silence_duration_ms=450),
        )

        # Collect segments
        transcript_parts = []
        total_confidence = 0.0
        segment_count = 0
        for seg in segments:
            transcript_parts.append(seg.text.strip())
            # avg_logprob is negative; convert to 0-1 confidence proxy
            if hasattr(seg, "avg_logprob"):
                conf = max(0.0, min(1.0, 1.0 + seg.avg_logprob / 1.5))
                total_confidence += conf
                segment_count += 1

        result["transcript"] = " ".join(transcript_parts).strip()
        if segment_count > 0:
            result["confidence"] = round(total_confidence / segment_count, 3)
        result["duration_seconds"] = round(info.duration, 1) if hasattr(info, "duration") else None

    except Exception as e:
        logger.error(f"STT transcription error: {e}")
        result["error"] = f"Transcription failed: {str(e)[:200]}"
    finally:
        # ALWAYS delete the temp file — no audio persisted
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    return result


def get_stt_status() -> Dict[str, Any]:
    """Check STT engine availability for the health/status endpoint."""
    settings = get_settings()
    model = _get_whisper_model()
    return {
        "available": model is not None,
        "engine": getattr(settings, "stt_engine", "faster-whisper"),
        "model_size": getattr(settings, "stt_model", "tiny"),
        "device": getattr(settings, "stt_device", "cpu"),
        "compute_type": getattr(settings, "stt_compute_type", "int8"),
        "local_processing": True,
        "audio_retained": False,
        "fallback_available": True,
        "fallback_engine": "Web Speech API (browser-native; client-side fallback with cloud processing)",
        "diagnostics": "faster-whisper operational" if model is not None else "faster-whisper model not loaded",
    }


def _mime_to_suffix(mime_type: str) -> str:
    if not mime_type:
        return ".webm"
    base = mime_type.split(";")[0].strip().lower()
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp4": ".mp4",
        "audio/x-m4a": ".mp4",
        "audio/m4a": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
    }
    return mapping.get(base, ".webm")

