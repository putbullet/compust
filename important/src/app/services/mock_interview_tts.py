"""
TTS (Text-to-Speech) service for AI Mock Interview.

Provides human-like, conversational neural voices for the AI interviewer.
Engine:
- Primary: edge-tts (studio-quality, zero-GPU, CPU-independent neural voices)
- Fallback: Browser-native SpeechSynthesis (handled gracefully on frontend if offline)

Features:
- Fast in-memory audio generation (audio/mpeg)
- Zero required API keys or paid accounts
- In-memory LRU cache for spoken prompts
- Automatic natural pacing and pause configuration
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

from ..config import get_settings

logger = logging.getLogger("compust.mock_interview.tts")

# Curated professional interviewer voices
TTS_PRESET_VOICES: List[Dict[str, Any]] = [
    {
        "id": "en-US-AndrewMultilingualNeural",
        "name": "Alex Mercer (Male - Natural & Conversational)",
        "gender": "male",
        "locale": "en-US",
        "is_default": True,
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Elena Vance (Female - Crisp & Professional)",
        "gender": "female",
        "locale": "en-US",
        "is_default": False,
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Marcus Stone (Male - Calm & Authoritative)",
        "gender": "male",
        "locale": "en-US",
        "is_default": False,
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Sarah Chen (Female - Warm & Articulate)",
        "gender": "female",
        "locale": "en-US",
        "is_default": False,
    },
    {
        "id": "en-GB-RyanNeural",
        "name": "David Sterling (Male UK - Precise & Formal)",
        "gender": "male",
        "locale": "en-GB",
        "is_default": False,
    },
    {
        "id": "en-GB-SoniaNeural",
        "name": "Victoria Croft (Female UK - Professional)",
        "gender": "female",
        "locale": "en-GB",
        "is_default": False,
    },
]

# Simple in-memory cache for synthesized audio (hash -> bytes)
_TTS_CACHE: Dict[str, bytes] = {}
_MAX_CACHE_ENTRIES = 50


def _get_cache_key(text: str, voice: str, rate: str, pitch: str) -> str:
    raw = f"{voice}::{rate}::{pitch}::{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> bytes:
    """
    Synthesize natural human speech from text using edge-tts.
    Returns MP3 audio bytes.
    """
    settings = get_settings()
    chosen_voice = voice or getattr(settings, "tts_voice", "en-US-AndrewMultilingualNeural")
    chosen_rate = rate or getattr(settings, "tts_rate", "-3%")
    chosen_pitch = pitch or getattr(settings, "tts_pitch", "+0Hz")

    clean_text = text.strip()
    if not clean_text:
        return b""

    cache_key = _get_cache_key(clean_text, chosen_voice, chosen_rate, chosen_pitch)
    if cache_key in _TTS_CACHE:
        return _TTS_CACHE[cache_key]

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

        # Cache synthesized audio
        if len(_TTS_CACHE) >= _MAX_CACHE_ENTRIES:
            # Drop oldest entry
            oldest_key = next(iter(_TTS_CACHE))
            del _TTS_CACHE[oldest_key]
        _TTS_CACHE[cache_key] = audio_bytes

        return audio_bytes
    except Exception as e:
        logger.warning(f"edge-tts synthesis failed: {e}")
        raise RuntimeError(f"Speech synthesis error: {e}")


def get_tts_status() -> Dict[str, Any]:
    """Check TTS availability and list available voices."""
    has_edge_tts = False
    try:
        import edge_tts
        has_edge_tts = True
    except ImportError:
        has_edge_tts = False

    settings = get_settings()
    return {
        "available": has_edge_tts,
        "engine": "edge-tts" if has_edge_tts else "browser-native-fallback",
        "default_voice": getattr(settings, "tts_voice", "en-US-AndrewMultilingualNeural"),
        "voices": TTS_PRESET_VOICES,
        "fallback_available": True,
        "fallback_engine": "Web SpeechSynthesis API",
    }
