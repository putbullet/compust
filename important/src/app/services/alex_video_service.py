"""
Alex Interviewer Video Service.

Provides question-to-video mapping, question text hash validation,
and asset verification for the photorealistic AI interviewer "Alex".

Key Guarantees:
- Deterministic question_text_hash validation prevents playing videos
  if question text has been edited.
- Verifies physical asset existence on disk before returning video URLs.
- Returns None whenever video is unavailable or stale, allowing the
  frontend/backend to fall back gracefully to the avatar / TTS pipeline.
- Single source of truth: src/app/content/interview_prep/alex_video_registry.json
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("compust.alex_video_service")

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content" / "interview_prep"
REGISTRY_PATH = CONTENT_DIR / "alex_video_registry.json"

# Static asset roots (frontend public directory and backend static directory)
FRONTEND_PUBLIC_DIR = BASE_DIR.parent.parent / "frontend" / "public"
BACKEND_STATIC_DIR = BASE_DIR / "static"


def normalize_text_for_hash(text: str) -> str:
    """
    Normalize question text for consistent cryptographic hashing.
    Strips markdown formatting, punctuation, casing, and extraneous whitespace.
    """
    if not text:
        return ""
    # Strip markdown symbols (*, _, `, #, [, ])
    clean = re.sub(r"[*`#_\[\]]", " ", text)
    # Convert to lowercase
    clean = clean.lower()
    # Replace non-alphanumeric chars with spaces
    clean = re.sub(r"[^\w\s]", " ", clean)
    # Collapse multiple whitespaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def compute_question_hash(text: str) -> str:
    """
    Compute a 16-character SHA-256 hash of normalized question text.
    Used to detect if stored question text has changed since video generation.
    """
    normalized = normalize_text_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class AlexVideoService:
    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or REGISTRY_PATH
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registered video assets from JSON."""
        if not self.registry_file.exists():
            self._registry = {}
            logger.info(f"Alex video registry not found at {self.registry_file}, initialized empty.")
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._registry = {item["question_id"]: item for item in data if "question_id" in item}
                elif isinstance(data, dict):
                    self._registry = data.get("videos", data)
                logger.info(f"Loaded {len(self._registry)} video entries from Alex registry.")
        except Exception as exc:
            logger.error(f"Failed to load Alex video registry from {self.registry_file}: {exc}")
            self._registry = {}

    def save_registry(self) -> None:
        """Save registry back to JSON."""
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({"interviewer": "alex", "version": "1.0", "videos": self._registry}, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self._registry)} Alex video entries to {self.registry_file}.")
        except Exception as exc:
            logger.error(f"Failed to save Alex video registry: {exc}")

    def verify_asset_on_disk(self, relative_path: str) -> bool:
        """
        Check whether the video asset exists either in frontend/public or backend static dir.
        relative_path is typically '/interviewer/alex/...'
        """
        clean_rel = relative_path.lstrip("/\\")
        
        # Check frontend/public
        fe_path = FRONTEND_PUBLIC_DIR / clean_rel
        if fe_path.is_file() and fe_path.stat().st_size > 0:
            return True

        # Check backend static
        be_path = BACKEND_STATIC_DIR / clean_rel
        if be_path.is_file() and be_path.stat().st_size > 0:
            return True

        return False

    def get_video_for_question(
        self,
        question_id: str,
        question_text: str,
        domain_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve Alex video metadata for a given question.
        
        Validations:
        1. Entry must exist in registry for `question_id`.
        2. Computed question_text_hash must match stored question_text_hash (or alternative accepted hashes).
        3. Media file must physically exist on disk.

        If any validation fails, returns None so caller can fall back gracefully.
        """
        if not question_id or question_id not in self._registry:
            return None

        entry = self._registry[question_id]

        # Hash validation
        expected_hash = entry.get("question_text_hash")
        current_hash = compute_question_hash(question_text)

        # Also allow matching against question_title or stored question_text in entry
        accepted_hashes = {expected_hash}
        if "question_text" in entry:
            accepted_hashes.add(compute_question_hash(entry["question_text"]))
        if "tts_text" in entry:
            accepted_hashes.add(compute_question_hash(entry["tts_text"]))

        if current_hash not in accepted_hashes:
            logger.warning(
                f"Alex video hash mismatch for question '{question_id}'. "
                f"Current text hash: '{current_hash}', expected: '{expected_hash}'. "
                f"Falling back to avatar/TTS."
            )
            return None

        video_path = entry.get("video_path")
        if not video_path:
            return None

        # Verify disk existence
        if not self.verify_asset_on_disk(video_path):
            logger.warning(
                f"Alex video file missing on disk for '{question_id}' at path '{video_path}'. "
                f"Falling back to avatar/TTS."
            )
            return None

        return {
            "question_id": question_id,
            "interviewer": entry.get("interviewer", "alex"),
            "question_type": entry.get("question_type", "technical"),
            "track": entry.get("track", domain_id or "security_engineering"),
            "video_path": video_path,
            "audio_path": entry.get("audio_path"),
            "duration_seconds": entry.get("duration_seconds", 5.0),
            "question_text_hash": expected_hash,
        }

    def register_video(
        self,
        question_id: str,
        question_text: str,
        video_path: str,
        audio_path: Optional[str] = None,
        question_type: str = "technical",
        track: str = "security_engineering",
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        """Register or update a video asset entry."""
        text_hash = compute_question_hash(question_text)
        entry = {
            "question_id": question_id,
            "interviewer": "alex",
            "question_type": question_type,
            "track": track,
            "question_text": question_text,
            "question_text_hash": text_hash,
            "video_path": video_path,
            "audio_path": audio_path,
            "duration_seconds": round(duration_seconds, 2),
        }
        self._registry[question_id] = entry
        self.save_registry()
        return entry

    def list_all_videos(self) -> List[Dict[str, Any]]:
        """Return all registered video entries."""
        return list(self._registry.values())

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status of registered videos."""
        total = len(self._registry)
        on_disk = 0
        missing = []

        for qid, entry in self._registry.items():
            v_path = entry.get("video_path", "")
            if self.verify_asset_on_disk(v_path):
                on_disk += 1
            else:
                missing.append({"question_id": qid, "path": v_path})

        return {
            "total_registered": total,
            "available_on_disk": on_disk,
            "missing_count": len(missing),
            "missing_assets": missing,
            "interviewer": "alex",
            "reference_portrait": "/interviewer/alex/identity/reference.jpg",
        }


# Global singleton instance
alex_video_service = AlexVideoService()
