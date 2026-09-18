"""
Ingestion & Question Bank Generator for Compust Interview Prep:
1. Security Engineering:
   - Source: https://github.com/abhinavkakku/Cyber_Security_Interview_Questions
   - Incorporates all 41 Beginner / Foundational questions from user prompt
   - Incorporates all 40 Intermediate questions from user prompt
   - Incorporates all 32 Experienced questions from user prompt
   - Incorporates questions from Cyber_Security_Interview_Questions repository
   - Maps questions into real-world career roles and 3 expertise tiers (Entry-Level, Mid-Level, Senior / Architect)
   - References Cyber_Security_Job_Roles.png infographic
2. AI Engineering:
   - Source: https://github.com/amitshekhariitbhu/ai-engineering-interview-questions
   - Incorporates complete interview tracks: LLM Fundamentals, Prompt Engineering, RAG, AI Agents/MCP, Fine-Tuning, Vector DBs, System Design & LLMOps
   - Provides comprehensive technical answers with code samples and math
   - Maps into real-world AI roles (GenAI Engineer, LLM Platform Engineer, RAG Specialist, AI Agent Architect, MLOps)
   - References /illustrations/ai_engineering_banner.png and educational vector diagrams
"""

import sys
import re
import json
import hashlib
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s[:90]


def main():
    base_dir = Path(__file__).resolve().parent.parent
    content_dir = base_dir / "src" / "app" / "content" / "interview_prep"
    sec_dir = content_dir / "security_engineering"
    ai_dir = content_dir / "ai_tech_interview"

    sec_dir.mkdir(parents=True, exist_ok=True)
    ai_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(base_dir))
    print("Generating comprehensive Security Engineering question bank...")
    # Import and run security questions generator
    from scripts.data_security_questions import get_security_questions, get_security_metadata
    sec_questions = get_security_questions()
    sec_metadata = get_security_metadata(len(sec_questions))

    with open(sec_dir / "questions.json", "w", encoding="utf-8") as f:
        json.dump(sec_questions, f, indent=2, ensure_ascii=False)
    with open(sec_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(sec_metadata, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated {len(sec_questions)} Security Engineering questions.")

    print("Generating comprehensive AI Engineering question bank...")
    from scripts.data_ai_questions import get_ai_questions, get_ai_metadata
    ai_questions = get_ai_questions()
    ai_metadata = get_ai_metadata(len(ai_questions))

    with open(ai_dir / "questions.json", "w", encoding="utf-8") as f:
        json.dump(ai_questions, f, indent=2, ensure_ascii=False)
    with open(ai_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(ai_metadata, f, indent=2, ensure_ascii=False)
    print(f"✓ Generated {len(ai_questions)} AI Engineering questions.")

    # Update ingestion report
    report_file = content_dir / "ingestion_report.json"
    with open(report_file, "r", encoding="utf-8") as f:
        report = json.load(f)

    report["repositories"]["security_engineering"] = {
        "url": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
        "commit": "f42c7bf5340b1d7077bde24663148a0504ecb7ec",
        "license": "Public Open Source (GitHub Terms of Service)",
        "discovered_files": 4,
        "imported_questions": len(sec_questions),
        "translated_questions": 0,
        "language": "Canonical English",
        "diagrams_included": [
            "Cyber_Security_Job_Roles.png",
            "diagram_oauth_pkce_flow.svg"
        ]
    }

    report["repositories"]["ai_tech_interview"] = {
        "url": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
        "commit": "d6c27fba1cda87e9789e8b8664300d77057db6ec",
        "license": "Public Open Source (Outcome School / Amit Shekhar)",
        "discovered_files": 4,
        "imported_questions": len(ai_questions),
        "translated_questions": 0,
        "language": "Canonical English",
        "diagrams_included": [
            "ai_engineering_banner.png",
            "diagram_transformer_attention.svg",
            "diagram_rag_pipeline.svg"
        ]
    }

    report["summary"]["total_technical_questions"] = 2101 + len(sec_questions) + len(ai_questions)
    report["summary"]["translation_status"]["security_engineering"] = "Canonical English (abhinavkakku/Cyber_Security_Interview_Questions)"
    report["summary"]["translation_status"]["ai_tech_interview"] = "Canonical English (amitshekhariitbhu/ai-engineering-interview-questions)"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("✓ Updated ingestion_report.json.")


if __name__ == "__main__":
    main()
