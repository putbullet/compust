"""
Comprehensive Content Builder for Compust Interview Prep Knowledge Center.
Grounds all material strictly in the 4 cloned GitHub repositories:
1. OBenner/data-engineering-interview-questions (English)
2. FeeiCN/security-engineering (Chinese -> Professional English with technical validation)
3. boost-devs/ai-tech-interview (Korean/Chinese -> Professional English with diagrams)
4. nas5w/interview-guide (English -> Behavioral Frameworks, STAR Method, Story Matrix, Prep Guides)
"""

import os
import re
import sys
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
REPOS_DIR = BASE_DIR / "scratch" / "repos"
CONTENT_DIR = BASE_DIR / "src" / "app" / "content" / "interview_prep"
PUBLIC_ILLUSTRATIONS = BASE_DIR / "frontend" / "public" / "illustrations"

COMMITS = {
    "data_engineering": "2a27b4e98a564b9d0fb1019ae3ba9a2c2e3f35db",
    "security_engineering": "d3713fe502cc90a29b32a678b824ff080262f847",
    "ai_tech_interview": "ee05fc3166a871cf2d4f749ce7bca2d6a9762305",
    "interview_guide": "50b3a0db428e4c644caa615021a444a0b2e6b92e",
}

def compute_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:80] or "item"

def sanitize_markdown(text: str) -> str:
    text = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"javascript:\s*", "", text, flags=re.IGNORECASE)
    return text

print("Starting Compust Ingestion Pipeline...")
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
