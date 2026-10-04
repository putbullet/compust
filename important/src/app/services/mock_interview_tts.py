"""
TTS (Text-to-Speech) service for AI Behavioral Mock Interview.

Provides human-like, conversational neural voices for the AI interviewer.
Engine hierarchy:
1. Piper (local offline neural TTS on CPU via piper-tts)
2. edge-tts (studio-quality, zero-GPU neural voices)
3. Browser-native Web SpeechSynthesis (fallback on client side)

Features:
- Multilingual voices: English (EN), French (FR), Dutch (NL)
- Automatic text normalization (cleaning markdown artifacts, pauses)
- Sentence splitting for low-latency streaming playback
- In-memory LRU cache for synthesized audio
- Fully offline capable on modest CPU laptops
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_settings

logger = logging.getLogger("compust.mock_interview.tts")

# Curated professional interviewer voices per language
TTS_PRESET_VOICES: List[Dict[str, Any]] = [
    # English (EN)
    {
        "id": "en-US-AndrewMultilingualNeural",
        "name": "Alex Mercer (Male - Natural & Conversational)",
        "gender": "male",
        "locale": "en-US",
        "language": "en",
        "is_default": True,
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Elena Vance (Female - Crisp & Professional)",
        "gender": "female",
        "locale": "en-US",
        "language": "en",
        "is_default": False,
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Marcus Stone (Male - Calm & Authoritative)",
        "gender": "male",
        "locale": "en-US",
        "language": "en",
        "is_default": False,
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Sarah Chen (Female - Warm & Articulate)",
        "gender": "female",
        "locale": "en-US",
        "language": "en",
        "is_default": False,
    },
    # French (FR)
    {
        "id": "fr-FR-HenriNeural",
        "name": "Henri Laurent (Homme - Calme & Professionnel)",
        "gender": "male",
        "locale": "fr-FR",
        "language": "fr",
        "is_default": False,
    },
    {
        "id": "fr-FR-DeniseNeural",
        "name": "Denise Moreau (Femme - Naturelle & Bienveillante)",
        "gender": "female",
        "locale": "fr-FR",
        "language": "fr",
        "is_default": False,
    },
    # Dutch (NL)
    {
        "id": "nl-NL-MaartenNeural",
        "name": "Maarten van Dijk (Man - Professioneel)",
        "gender": "male",
        "locale": "nl-NL",
        "language": "nl",
        "is_default": False,
    },
    {
        "id": "nl-NL-FennaNeural",
        "name": "Fenna de Boer (Vrouw - Vriendelijk & Duidelijk)",
        "gender": "female",
        "locale": "nl-NL",
        "language": "nl",
        "is_default": False,
    },
]

# Simple in-memory cache for synthesized audio (hash -> bytes)
_TTS_CACHE: Dict[str, bytes] = {}
_MAX_CACHE_ENTRIES = 100


def normalize_speech_text(text: str) -> str:
    """
    Clean text for natural spoken delivery:
    - Removes markdown formatting (asterisks, backticks, hashes)
    - Normalizes punctuation and ellipses
    - Removes URLs and bracketed cues
    """
    cleaned = re.sub(r"[*_~`#]", "", text)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\(https?://\S+\)", "", cleaned)
    cleaned = re.sub(r"\.{2,}", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_into_sentences(text: str) -> List[str]:
    """Split speech text into natural sentences for incremental playback."""
    clean = normalize_speech_text(text)
    # Match sentences ending with ., !, or ?
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    return [s.strip() for s in sentences if s.strip()]


def _get_cache_key(text: str, voice: str, rate: str, pitch: str) -> str:
    raw = f"{voice}::{rate}::{pitch}::{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_default_voice_for_language(language: str) -> str:
    lang = language.lower() if language else "en"
    for v in TTS_PRESET_VOICES:
        if v.get("language") == lang:
            return v["id"]
    return "en-US-AndrewMultilingualNeural"


async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
    language: str = "en",
) -> bytes:
    """
    Synthesize natural human speech from text.
    Uses Piper if an offline voice model is configured/present,
    falling back to edge-tts.
    Returns audio bytes (audio/mpeg).
    """
    clean_text = normalize_speech_text(text)
    if not clean_text:
        return b""

    settings = get_settings()
    chosen_voice = voice or getattr(settings, "tts_voice", None) or _get_default_voice_for_language(language)
    chosen_rate = rate or getattr(settings, "tts_rate", "-2%")
    chosen_pitch = pitch or getattr(settings, "tts_pitch", "+0Hz")

    cache_key = _get_cache_key(clean_text, chosen_voice, chosen_rate, chosen_pitch)
    if cache_key in _TTS_CACHE:
        return _TTS_CACHE[cache_key]

    # Try Piper offline neural TTS if model path exists
    piper_model_path = getattr(settings, "piper_model_path", None)
    if piper_model_path and Path(piper_model_path).exists():
        try:
            import piper
            piper_voice = piper.PiperVoice.load(str(piper_model_path))
            out_buf = io.BytesIO()
            piper_voice.synthesize(clean_text, out_buf)
            audio_bytes = out_buf.getvalue()
            if audio_bytes:
                _cache_audio(cache_key, audio_bytes)
                return audio_bytes
        except Exception as p_err:
            logger.warning(f"Piper synthesis fallback to edge-tts: {p_err}")

    # Primary neural engine: edge-tts
    try:
        import edge_tts

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=chosen_voice,
            rate=chosen_rate,
            pitch=chosen_pitch,
        )

        audio_buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.extend(chunk["data"])

        audio_bytes = bytes(audio_buffer)
        _cache_audio(cache_key, audio_bytes)
        return audio_bytes
    except Exception as e:
        logger.warning(f"edge-tts synthesis failed: {e}")
        raise RuntimeError(f"Speech synthesis error: {e}")


def _cache_audio(cache_key: str, audio_bytes: bytes) -> None:
    if len(_TTS_CACHE) >= _MAX_CACHE_ENTRIES:
        oldest_key = next(iter(_TTS_CACHE))
        del _TTS_CACHE[oldest_key]
    _TTS_CACHE[cache_key] = audio_bytes


def get_tts_status() -> Dict[str, Any]:
    """Check TTS availability and list available voices."""
    has_edge_tts = False
    try:
        import edge_tts
        has_edge_tts = True
    except ImportError:
        has_edge_tts = False

    has_piper = False
    try:
        import piper
        has_piper = True
    except ImportError:
        has_piper = False

    settings = get_settings()
    active_engine = "piper" if (has_piper and getattr(settings, "piper_model_path", None)) else ("edge-tts" if has_edge_tts else "browser-native-fallback")

    return {
        "available": has_edge_tts or has_piper,
        "engine": active_engine,
        "has_piper": has_piper,
        "has_edge_tts": has_edge_tts,
        "default_voice": getattr(settings, "tts_voice", "en-US-AndrewMultilingualNeural"),
        "voices": TTS_PRESET_VOICES,
        "fallback_available": True,
        "fallback_engine": "Web SpeechSynthesis API",
    }
