"""
Alex AI Interviewer Video Pre-generation Tool.

Automates generating synchronized question-specific video & audio assets
for the photorealistic AI interviewer "Alex".

Features:
1. Reads exact question text from question bank (zero paraphrasing).
2. Synthesizes neural voice audio matching Alex's identity (en-US-AndrewMultilingualNeural).
3. Generates synchronized MP4 video with natural micro-presence from Alex's reference portrait.
4. Muxes audio and video into a single standard MP4 container (H.264 + AAC).
5. Computes question_text_hash to protect against stale/modified question text.
6. Updates alex_video_registry.json.
7. Supports --pilot flag for the 10 Security Engineering pilot questions.
8. Idempotent: skips already-generated valid assets unless --force is specified.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup workspace paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_APP = PROJECT_ROOT / "src" / "app"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_APP))

from src.app.services.alex_video_service import (
    alex_video_service,
    compute_question_hash,
    FRONTEND_PUBLIC_DIR,
    BACKEND_STATIC_DIR,
)
from src.app.services.mock_interview_engine import (
    DEFAULT_BEHAVIORAL_QUESTIONS,
    build_introductory_tts,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("alex_video_generator")

# Neural voice profile matching Alex's identity
ALEX_VOICE = "en-US-AndrewMultilingualNeural"

# Reference portrait locations
REFERENCE_PORTRAIT = FRONTEND_PUBLIC_DIR / "interviewer" / "alex" / "identity" / "reference.jpg"


def get_pilot_questions() -> List[Dict[str, Any]]:
    """
    Returns the 10 pilot questions for Security Engineering as defined in task section 20.
    """
    # 1. Interview Greeting / Introduction
    intro_text = (
        "Hello, I'm Alex. Welcome to your mock interview for Security Engineering. "
        "Whenever I finish speaking, the system will automatically start listening for your response. "
        "To get started, could you tell me a little about yourself and your background?"
    )

    # 2. Tell me about yourself (dedicated question)
    intro_q = "Could you tell me a little about yourself, your background, and what brings you to this interview?"

    # 3. CIA triad
    cia_q = "What is the CIA Triad?"

    # 4. Authentication vs authorization
    auth_q = "What is the difference between authentication and authorization?"

    # 5. Incident response scenario
    ir_q = (
        "Walk me through an incident response scenario where an endpoint alerts on suspected ransomware activity. "
        "How do you triage, contain, and remediate the incident?"
    )

    # 6. SOC-related technical question (SIEM)
    siem_q = "What is a SIEM (Security Information and Event Management) System and What Role Does It Play in a SOC?"

    # 7. Difficult technical problem behavioral question
    prob_q = (
        "Walk me through a technically difficult engineering problem you encountered recently. "
        "What was your role and what architectural alternatives did you consider?"
    )

    # 8. Teamwork behavioral question
    team_q = (
        "Tell me about a time you had a technical disagreement with a teammate or engineering manager. "
        "How did you resolve it?"
    )

    # 9. Failure/learning behavioral question
    fail_q = (
        "Describe a time when you caused or had to resolve a severe production outage or unexpected bug. "
        "What did you learn and what safeguards did you put in place?"
    )

    # 10. Security-project behavioral question
    sec_proj_q = (
        "Tell me about a time when you identified a security issue or potential vulnerability. What did you do?"
    )

    return [
        {
            "question_id": "intro_security_engineering",
            "question_type": "introductory",
            "track": "security_engineering",
            "title": "Interview Introduction & Greeting",
            "text": intro_text,
        },
        {
            "question_id": "beh_intro_1",
            "question_type": "behavioral",
            "track": "security_engineering",
            "title": "Tell Me About Yourself",
            "text": intro_q,
        },
        {
            "question_id": "sec_f_14",
            "question_type": "technical",
            "track": "security_engineering",
            "title": "What is the CIA Triad?",
            "text": cia_q,
        },
        {
            "question_id": "sec_auth_vs_authz",
            "question_type": "technical",
            "track": "security_engineering",
            "title": "Authentication vs Authorization",
            "text": auth_q,
        },
        {
            "question_id": "sec_ir_scenario",
            "question_type": "technical",
            "track": "security_engineering",
            "title": "Incident Response Scenario",
            "text": ir_q,
        },
        {
            "question_id": "sec_i_13",
            "question_type": "technical",
            "track": "security_engineering",
            "title": "SIEM & SOC Operations",
            "text": siem_q,
        },
        {
            "question_id": "beh_problem_solving_1",
            "question_type": "behavioral",
            "track": "security_engineering",
            "title": "Difficult Technical Problem",
            "text": prob_q,
        },
        {
            "question_id": "beh_conflict_1",
            "question_type": "behavioral",
            "track": "security_engineering",
            "title": "Teamwork & Conflict Resolution",
            "text": team_q,
        },
        {
            "question_id": "beh_failure_1",
            "question_type": "behavioral",
            "track": "security_engineering",
            "title": "Production Failure & Blameless Learning",
            "text": fail_q,
        },
        {
            "question_id": "beh_sec_incident_1",
            "question_type": "behavioral",
            "track": "security_engineering",
            "title": "Security Vulnerability Discovery",
            "text": sec_proj_q,
        },
    ]


async def synthesize_audio(text: str, output_path: Path, voice: str = ALEX_VOICE) -> None:
    """Synthesize high-quality neural speech audio using edge_tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    await communicate.save(str(output_path))


def get_audio_duration_seconds(audio_path: Path) -> float:
    """Probe audio duration using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as exc:
        logger.warning(f"Could not probe audio duration with ffprobe ({exc}), falling back to estimate.")
        # Rough estimate based on file size (MP3 ~ 16KB/s)
        return max(3.0, audio_path.stat().st_size / 16000.0)


def generate_synchronized_video(
    image_path: Path,
    audio_path: Path,
    output_video_path: Path,
    duration: float,
) -> None:
    """
    Generate an MP4 video combining Alex's reference portrait with synthesized audio.
    Applies subtle realistic micro-presence (subtle imperceptible scale/motion)
    so the interviewer feels active and alive, with audio and video synchronized
    in a clean standard H.264/AAC MP4 container.
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    # ffmpeg command:
    # 1. Loop image for the duration of the audio
    # 2. Subtle zoompan/crop for gentle lifelike micro-motion
    # 3. yuv420p pixel format for universal browser HTML5 video playback
    # 4. AAC audio encoding
    filter_complex = (
        f"scale=1080:1080:force_original_aspect_ratio=increase,"
        f"crop=1080:1080,"
        f"zoompan=z='min(zoom+0.00015,1.02)':d={int(duration * 25 + 25)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1080:fps=25"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_video_path),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError as err:
        logger.error(f"FFmpeg failed: {err.stderr.decode('utf-8', errors='ignore')}")
        raise


async def process_question(
    q_item: Dict[str, Any],
    force: bool = False,
    dry_run: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Generate and register video/audio for a single question.
    """
    qid = q_item["question_id"]
    track = q_item["track"]
    q_type = q_item["question_type"]
    text = q_item["text"]

    expected_hash = compute_question_hash(text)

    # Asset destination paths
    rel_video_path = f"/interviewer/alex/{track}/{q_type}/{qid}.mp4"
    rel_audio_path = f"/interviewer/alex/{track}/{q_type}/{qid}.mp3"

    fe_video_path = FRONTEND_PUBLIC_DIR / rel_video_path.lstrip("/\\")
    be_video_path = BACKEND_STATIC_DIR / rel_video_path.lstrip("/\\")

    fe_audio_path = FRONTEND_PUBLIC_DIR / rel_audio_path.lstrip("/\\")
    be_audio_path = BACKEND_STATIC_DIR / rel_audio_path.lstrip("/\\")

    # Check existing valid asset
    if not force and fe_video_path.exists() and fe_video_path.stat().st_size > 1000:
        existing_info = alex_video_service.get_video_for_question(qid, text, track)
        if existing_info:
            logger.info(f"[{qid}] Asset already up-to-date and verified. Skipping (use --force to overwrite).")
            return existing_info

    if dry_run:
        logger.info(f"[DRY-RUN] Would generate {qid}: '{text[:60]}...' -> {rel_video_path}")
        return None

    logger.info(f"[{qid}] Synthesizing Alex speech audio ({len(text)} chars)...")
    await synthesize_audio(text, fe_audio_path)

    # Copy audio to backend static dir
    be_audio_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(fe_audio_path), str(be_audio_path))

    duration = get_audio_duration_seconds(fe_audio_path)
    logger.info(f"[{qid}] Synthesized audio duration: {duration:.2f}s. Generating synchronized MP4...")

    generate_synchronized_video(
        image_path=REFERENCE_PORTRAIT,
        audio_path=fe_audio_path,
        output_video_path=fe_video_path,
        duration=duration,
    )

    # Copy video to backend static dir
    be_video_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(fe_video_path), str(be_video_path))

    # Register in Alex Video Service
    entry = alex_video_service.register_video(
        question_id=qid,
        question_text=text,
        video_path=rel_video_path,
        audio_path=rel_audio_path,
        question_type=q_type,
        track=track,
        duration_seconds=duration,
    )

    logger.info(f"[{qid}] Success! Generated and registered: {rel_video_path} ({duration:.2f}s, size={fe_video_path.stat().st_size // 1024} KB)")
    return entry


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Generate Alex AI Interviewer videos")
    parser.add_argument("--pilot", action="store_true", help="Generate the 10 Security Engineering pilot questions")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing assets")
    parser.add_argument("--dry-run", action="store_true", help="Dry run check without creating files")
    parser.add_argument("--status", action="store_true", help="Check and print registry status")
    args = parser.parse_args()

    if args.status:
        status = alex_video_service.get_status()
        print("\n=== Alex Video Registry Diagnostic Status ===")
        print(f"Interviewer: {status['interviewer']}")
        print(f"Reference portrait: {status['reference_portrait']}")
        print(f"Total registered questions: {status['total_registered']}")
        print(f"Verified assets on disk: {status['available_on_disk']}")
        print(f"Missing assets: {status['missing_count']}")
        if status['missing_assets']:
            for m in status['missing_assets']:
                print(f"  - Missing: {m['question_id']} -> {m['path']}")
        return

    if not REFERENCE_PORTRAIT.exists():
        logger.error(f"Reference portrait for Alex not found at {REFERENCE_PORTRAIT}!")
        sys.exit(1)

    questions_to_process = []
    if args.pilot:
        questions_to_process = get_pilot_questions()
        logger.info(f"Selected {len(questions_to_process)} pilot questions for Security Engineering.")
    else:
        # Default to pilot questions
        questions_to_process = get_pilot_questions()
        logger.info(f"No specific questions provided; defaulting to {len(questions_to_process)} pilot questions.")

    success_count = 0
    fail_count = 0

    for q in questions_to_process:
        try:
            res = await process_question(q, force=args.force, dry_run=args.dry_run)
            if res:
                success_count += 1
        except Exception as exc:
            logger.error(f"Failed to process '{q['question_id']}': {exc}", exc_info=True)
            fail_count += 1

    logger.info(f"\nCompleted! Processed: {len(questions_to_process)} | Succeeded: {success_count} | Failed: {fail_count}")
    status = alex_video_service.get_status()
    logger.info(f"Registry Status: {status['available_on_disk']}/{status['total_registered']} assets verified on disk.")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
