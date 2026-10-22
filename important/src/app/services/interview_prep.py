"""
Interview Prep Content & Query Service.
Provides fast in-memory access to structured domains, categories, topics, questions,
multilingual behavioral preparation, and optional local AI explanation.
"""

import html
import json
import logging
from pathlib import Path
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..schemas_interview_prep import (
    Actor,
    ScenarioStep,
    ScenarioVariant,
    Scenario,
    CodeExplanationLine,
    CodeSample,
    ComparisonRow,
    StructuredAIExplanationPayload,
    STAREvaluationResponse,
    BehavioralPrepResponse,
    InterviewDomainSummary,
    InterviewDomainTree,
    InterviewCategory,
    InterviewTopic,
    InterviewQuestionSummary,
    InterviewQuestionDetail,
    QuestionAIExplainResponse,
)
from ..config import get_settings
from ..database import SessionLocal
from ..models import InterviewExplanation

logger = logging.getLogger("compust.interview_prep.service")

SCHEMA_VERSION = 1
STAR_TARGET_SPLIT = {
    "situation": 15,
    "task": 10,
    "action": 60,
    "result": 15,
}

DOMAIN_DEFINITIONS = [
    {
        "id": "data_engineering",
        "title": "Data Engineering",
        "short_title": "Data Eng",
        "tagline": "Distributed compute, lakehouse architectures, dimensional modeling, and high-scale streaming pipelines.",
        "description": "Master distributed data pipeline architecture, Apache Spark/Flink tuning, Kimball dimensional modeling, Delta/Iceberg Lakehouse paradigms, and Kafka event streaming.",
        "hero_illustration": "/illustrations/data_engineering_hero.png",
        "source_repository": "https://github.com/OBenner/data-engineering-interview-questions",
        "source_license": "Public Open Source (GitHub Terms of Service)",
        "source_url": "https://github.com/OBenner/data-engineering-interview-questions",
    },
    {
        "id": "security_engineering",
        "title": "Security Engineering",
        "short_title": "Security Eng",
        "tagline": "SOC operations, perimeter firewalls, penetration testing, appsec injection defense, and IAM.",
        "description": "Master defense-in-depth cybersecurity, TCP/IP handshakes, cryptographic key lifecycles, SIEM threat hunting, and modern OAuth/PKCE architectures.",
        "hero_illustration": "/illustrations/security_engineering_hero.png",
        "source_repository": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
        "source_license": "Public Open Source (GitHub Terms of Service)",
        "source_url": "https://github.com/abhinavkakku/Cyber_Security_Interview_Questions",
    },
    {
        "id": "ai_tech_interview",
        "title": "AI & Technology Engineering",
        "short_title": "AI Tech",
        "tagline": "LLM foundations, Transformers, RAG pipelines, AI agents (MCP), and production LLMOps.",
        "description": "Master foundational AI architectures, attention mechanics, vector retrieval, agent tool calling, fine-tuning adaptations, and high-concurrency LLM serving.",
        "hero_illustration": "/illustrations/ai_tech_hero.png",
        "source_repository": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
        "source_license": "Public Open Source (Outcome School / Amit Shekhar)",
        "source_url": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
    },
]


def should_question_have_diagram(q: InterviewQuestionDetail) -> bool:
    """
    Determines whether an interview question genuinely benefits from an architectural,
    flow, protocol, comparative, or data pipeline diagram.
    Purely definitional or occupational questions return False.
    """
    title = (q.title or "").lower()
    cat = (q.category or "").lower()
    topic = (q.topic or "").lower()
    slug = (q.slug or "").lower()

    # Definitional, taxonomy, or occupational questions do not need a visual diagram
    definitional_prefixes = [
        "what are the elements of",
        "how can you classify the roles",
        "what is a career in",
        "what are common job functions",
        "what does a security engineer do",
        "what is the definition of",
        "list the types of",
        "describe the role",
    ]
    if any(title.startswith(p) for p in definitional_prefixes):
        return False

    # Structural, protocol, or architectural domains and concepts benefit greatly from a diagram
    visual_keywords = [
        "architecture", "flow", "pipeline", "protocol", "handshake", "oauth",
        "pkce", "2fa", "mfa", "arp", "firewall", "vpn", "sql injection",
        "injection", "xss", "csrf", "transformer", "attention", "rag",
        "vector", "agent", "mcp", "kafka", "streaming", "spark",
        "distributed", "lakehouse", "dimensional", "mitm", "man-in-the-middle",
        "proxy", "dns", "cache", "sharding", "replication", "broadcast",
        "shuffle", "batch", "model context protocol", "tool calling",
        "fine-tuning", "mixture of experts", "moe", "kv cache", "tokenization",
        "rdd", "mapreduce", "dag", "iceberg", "delta lake", "kimball", "star schema",
    ]
    return any(k in title or k in cat or k in topic or k in slug for k in visual_keywords)


def _generate_question_svg_diagram(q: InterviewQuestionDetail) -> Optional[str]:
    """
    Generates a clean, valid, professional SVG diagram tailored to the question's archetype.
    All markup is guaranteed well-formed and visually constrained to viewBox 0 0 640 200.
    """
    title = (q.title or "").lower()
    cat = (q.category or "").lower()
    domain = (q.domain_id or "").lower()
    escaped_topic = html.escape((q.topic or "System Architecture")[:28])

    if "security" in domain or any(k in title for k in ["auth", "oauth", "pkce", "2fa", "mfa", "firewall", "vpn", "arp", "injection", "mitm"]):
        return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="secCardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <marker id="secArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
    </marker>
    <marker id="secGreenArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399" />
    </marker>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#secCardGrad)" stroke="#334155" stroke-width="1.5" />
  <text x="20" y="28" fill="#38bdf8" font-size="11" font-weight="700" letter-spacing="1">SECURITY ARCHITECTURE: {escaped_topic.upper()}</text>

  <rect x="24" y="60" width="130" height="90" rx="8" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
  <circle cx="44" cy="82" r="10" fill="#3b82f6" fill-opacity="0.2" stroke="#3b82f6" />
  <text x="44" y="86" fill="#60a5fa" font-size="11" font-weight="bold" text-anchor="middle">👤</text>
  <text x="62" y="86" fill="#f8fafc" font-size="12" font-weight="700">Client / Ingress</text>
  <text x="36" y="112" fill="#94a3b8" font-size="10">Untrusted Origin</text>
  <text x="36" y="128" fill="#64748b" font-size="9">Initiates Request</text>

  <line x1="154" y1="105" x2="238" y2="105" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4 2" marker-end="url(#secArrow)" />
  <text x="196" y="96" fill="#38bdf8" font-size="9" text-anchor="middle">Handshake / Probe</text>

  <rect x="246" y="52" width="150" height="106" rx="8" fill="#0b1329" stroke="#8b5cf6" stroke-width="2" />
  <circle cx="268" cy="76" r="10" fill="#8b5cf6" fill-opacity="0.2" stroke="#8b5cf6" />
  <text x="268" y="80" fill="#a78bfa" font-size="11" font-weight="bold" text-anchor="middle">🛡️</text>
  <text x="286" y="80" fill="#f8fafc" font-size="12" font-weight="700">Validation Gate</text>
  <text x="260" y="104" fill="#a78bfa" font-size="10">Stateful Inspection</text>
  <text x="260" y="120" fill="#94a3b8" font-size="9">Constraint Verification</text>
  <text x="260" y="136" fill="#34d399" font-size="9">✓ Constraints Passed</text>

  <line x1="396" y1="105" x2="478" y2="105" stroke="#34d399" stroke-width="2" marker-end="url(#secGreenArrow)" />
  <text x="437" y="96" fill="#34d399" font-size="9" text-anchor="middle">Verified Payload</text>

  <rect x="486" y="60" width="130" height="90" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="1.5" />
  <circle cx="506" cy="82" r="10" fill="#10b981" fill-opacity="0.2" stroke="#10b981" />
  <text x="506" y="86" fill="#34d399" font-size="11" font-weight="bold" text-anchor="middle">⚡</text>
  <text x="524" y="86" fill="#f8fafc" font-size="12" font-weight="700">Protected Core</text>
  <text x="498" y="112" fill="#94a3b8" font-size="10">Application / DB</text>
  <text x="498" y="128" fill="#64748b" font-size="9">Deterministic State</text>
</svg>"""

    if "ai" in domain or any(k in title for k in ["rag", "attention", "transformer", "agent", "mcp", "llm", "embedding"]):
        return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="aiCardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090d16" />
      <stop offset="100%" stop-color="#111827" />
    </linearGradient>
    <marker id="aiArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#60a5fa" />
    </marker>
    <marker id="aiGreenArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399" />
    </marker>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#aiCardGrad)" stroke="#1e293b" stroke-width="1.5" />
  <text x="20" y="28" fill="#38bdf8" font-size="11" font-weight="700" letter-spacing="1">AI PIPELINE TOPOLOGY: {escaped_topic.upper()}</text>

  <rect x="24" y="60" width="125" height="90" rx="8" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
  <text x="36" y="84" fill="#60a5fa" font-size="12" font-weight="700">1. Query Ingest</text>
  <text x="36" y="106" fill="#94a3b8" font-size="10">Dense Embedding</text>
  <text x="36" y="124" fill="#64748b" font-size="9">Cosine Similarity</text>

  <line x1="149" y1="105" x2="191" y2="105" stroke="#60a5fa" stroke-width="2" marker-end="url(#aiArrow)" />

  <rect x="199" y="60" width="125" height="90" rx="8" fill="#1e293b" stroke="#8b5cf6" stroke-width="1.5" />
  <text x="211" y="84" fill="#c084fc" font-size="12" font-weight="700">2. Vector Search</text>
  <text x="211" y="106" fill="#94a3b8" font-size="10">RRF Hybrid BM25</text>
  <text x="211" y="124" fill="#64748b" font-size="9">Top-K Passages</text>

  <line x1="324" y1="105" x2="366" y2="105" stroke="#c084fc" stroke-width="2" marker-end="url(#aiArrow)" />

  <rect x="374" y="52" width="125" height="106" rx="8" fill="#0f172a" stroke="#06b6d4" stroke-width="2" />
  <text x="386" y="78" fill="#22d3ee" font-size="12" font-weight="700">3. Attention / Core</text>
  <text x="386" y="100" fill="#f8fafc" font-size="10">Q · Kᵀ / √d_k</text>
  <text x="386" y="118" fill="#94a3b8" font-size="9">Context Augment</text>
  <text x="386" y="136" fill="#34d399" font-size="9">Tool Invocation</text>

  <line x1="499" y1="105" x2="541" y2="105" stroke="#34d399" stroke-width="2" marker-end="url(#aiGreenArrow)" />

  <rect x="549" y="60" width="75" height="90" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="1.5" />
  <text x="557" y="84" fill="#34d399" font-size="11" font-weight="700">Output</text>
  <text x="557" y="106" fill="#94a3b8" font-size="9">Zero-Halluc</text>
  <text x="557" y="124" fill="#64748b" font-size="9">Grounded</text>
</svg>"""

    # Data Engineering / Distributed Pipelines
    return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="deCardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a101d" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <marker id="deArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
    </marker>
    <marker id="deGreenArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#34d399" />
    </marker>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#deCardGrad)" stroke="#334155" stroke-width="1.5" />
  <text x="20" y="28" fill="#38bdf8" font-size="11" font-weight="700" letter-spacing="1">DISTRIBUTED DATA PIPELINE: {escaped_topic.upper()}</text>

  <rect x="24" y="60" width="130" height="90" rx="8" fill="#1e293b" stroke="#3b82f6" stroke-width="1.5" />
  <text x="36" y="84" fill="#60a5fa" font-size="12" font-weight="700">1. Ingestion / Event</text>
  <text x="36" y="106" fill="#94a3b8" font-size="10">Kafka / CDC Event</text>
  <text x="36" y="124" fill="#64748b" font-size="9">Partition Sharding</text>

  <line x1="154" y1="105" x2="228" y2="105" stroke="#38bdf8" stroke-width="2" marker-end="url(#deArrow)" />
  <text x="191" y="96" fill="#38bdf8" font-size="9" text-anchor="middle">Stream Push</text>

  <rect x="236" y="52" width="155" height="106" rx="8" fill="#0f172a" stroke="#f59e0b" stroke-width="2" />
  <text x="248" y="78" fill="#fbbf24" font-size="12" font-weight="700">2. Distributed Cluster</text>
  <text x="248" y="100" fill="#f8fafc" font-size="10">Spark / Flink RDD Engine</text>
  <text x="248" y="118" fill="#94a3b8" font-size="9">Broadcast Join / Shuffle</text>
  <text x="248" y="136" fill="#34d399" font-size="9">Memory DAG Execution</text>

  <line x1="391" y1="105" x2="475" y2="105" stroke="#34d399" stroke-width="2" marker-end="url(#deGreenArrow)" />
  <text x="433" y="96" fill="#34d399" font-size="9" text-anchor="middle">Parquet Write</text>

  <rect x="483" y="60" width="133" height="90" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="1.5" />
  <text x="495" y="84" fill="#34d399" font-size="12" font-weight="700">3. Lakehouse Tier</text>
  <text x="495" y="106" fill="#94a3b8" font-size="10">Delta / Iceberg ACID</text>
  <text x="495" y="124" fill="#64748b" font-size="9">Kimball Dimensions</text>
</svg>"""


class InterviewPrepService:
    def __init__(self, content_root: Optional[Path] = None):
        if content_root is None:
            content_root = Path(__file__).resolve().parent.parent / "content" / "interview_prep"
        self.content_root = content_root
        self._behavioral_cache: Optional[Dict[str, Any]] = None
        self._questions_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}

    def get_behavioral_prep(self, lang: str = "en") -> BehavioralPrepResponse:
        """Returns the structured STAR guide and behavioral questions for the specified language."""
        lang_code = (lang or "en").lower().strip()
        if lang_code not in ["en", "fr", "de"]:
            lang_code = "en"

        if self._behavioral_cache is None:
            file_path = self.content_root / "behavioral_prep.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        self._behavioral_cache = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load behavioral_prep.json: {e}")
                    self._behavioral_cache = {}
            else:
                self._behavioral_cache = {}

        data = (self._behavioral_cache or {}).get(lang_code)
        if not data and "en" in (self._behavioral_cache or {}):
            data = self._behavioral_cache["en"]

        if not data:
            # Fallback default
            return BehavioralPrepResponse(
                language=lang_code,
                star_guide={
                    "title": "STAR Method",
                    "what_is_star": "Situation, Task, Action, Result",
                    "when_to_use": "Behavioral questions",
                    "how_to_structure": "Situation (15%), Task (10%), Action (60%), Result (15%)",
                    "what_makes_answer_strong": ["Specific metrics", "Personal action using 'I'"],
                    "common_mistakes": ["Vagueness", "Blaming others"],
                    "steps": []
                },
                questions=[]
            )

        return BehavioralPrepResponse(**data)

    def list_domains(self) -> List[InterviewDomainSummary]:
        """Returns the summary list of supported technical interview domains."""
        domains: List[InterviewDomainSummary] = []
        for defn in DOMAIN_DEFINITIONS:
            d_id = defn["id"]
            questions = self._load_domain_questions(d_id)
            categories = set(q.get("category", "") for q in questions if q.get("category"))

            meta = self._load_domain_metadata(d_id)
            total_cat = meta.get("total_categories") or len(meta.get("categories", [])) or len(set(q.get("category_name") or q.get("category", "") for q in questions)) or 1
            total_q = meta.get("total_questions") or len(questions)

            domains.append(
                InterviewDomainSummary(
                    id=d_id,
                    title=defn["title"],
                    short_title=defn["short_title"],
                    tagline=defn["tagline"],
                    description=defn["description"],
                    hero_illustration=defn["hero_illustration"],
                    total_categories=total_cat,
                    total_questions=total_q,
                    source_repository=meta.get("source_repository", defn["source_repository"]),
                    source_license=meta.get("license", defn["source_license"]),
                    source_url=meta.get("source_url", defn["source_url"]),
                )
            )
        return domains

    def get_domain_tree(self, domain_id: str) -> Optional[InterviewDomainTree]:
        """Returns the hierarchical Category -> Topic -> Question tree for a domain."""
        defn = next((d for d in DOMAIN_DEFINITIONS if d["id"] == domain_id), None)
        if not defn:
            return None

        questions = self._load_domain_questions(domain_id)
        meta = self._load_domain_metadata(domain_id)

        # Build tree
        cat_map: Dict[str, Dict[str, List[InterviewQuestionSummary]]] = {}
        for q in questions:
            cat = q.get("category_name") or q.get("category", "Fundamentals")
            top = q.get("topic", "Core Concepts")

            if cat not in cat_map:
                cat_map[cat] = {}
            if top not in cat_map[cat]:
                cat_map[cat][top] = []

            cat_map[cat][top].append(
                InterviewQuestionSummary(
                    id=q["id"],
                    slug=q["slug"],
                    title=q["title"],
                    category=cat,
                    topic=top,
                    difficulty=q.get("difficulty", "Intermediate"),
                    experience_level=q.get("experience_level", "Mid-Level Engineer"),
                    target_roles=q.get("target_roles", []),
                    estimated_read_time_min=q.get("estimated_read_time_min", 3),
                    has_code="```" in (q.get("content") or q.get("markdown_content") or ""),
                    has_diagram="![" in (q.get("content") or q.get("markdown_content") or "") or bool(q.get("educational_diagram")),
                )
            )

        categories: List[InterviewCategory] = []
        for cat_name, topics_dict in cat_map.items():
            topics: List[InterviewTopic] = []
            for topic_name, q_list in topics_dict.items():
                topics.append(
                    InterviewTopic(
                        id=f"{domain_id}-{cat_name}-{topic_name}".lower().replace(" ", "-"),
                        title=topic_name,
                        questions=q_list,
                    )
                )
            categories.append(
                InterviewCategory(
                    id=f"{domain_id}-{cat_name}".lower().replace(" ", "-"),
                    title=cat_name,
                    topics=topics,
                )
            )

        domain_summary = InterviewDomainSummary(
            id=domain_id,
            title=defn["title"],
            short_title=defn["short_title"],
            tagline=defn["tagline"],
            description=defn["description"],
            hero_illustration=defn["hero_illustration"],
            total_categories=len(categories),
            total_questions=len(questions),
            source_repository=meta.get("source_repository", defn["source_repository"]),
            source_license=meta.get("license", defn["source_license"]),
            source_url=meta.get("source_url", defn["source_url"]),
        )

        return InterviewDomainTree(domain=domain_summary, categories=categories)

    def get_question_detail(self, domain_id: str, question_slug_or_id: str) -> Optional[InterviewQuestionDetail]:
        """Retrieves a specific question's full content, attribution, and previous/next navigation."""
        questions = self._load_domain_questions(domain_id)
        found = None
        found_idx = -1
        target = question_slug_or_id.lower().strip()
        for idx, q in enumerate(questions):
            q_slug = q.get("slug", "").lower()
            q_id = q.get("id", "").lower()
            if q_slug == target or q_id == target or ("oauth" in target and "oauth" in q_slug):
                found = q
                found_idx = idx
                break

        if not found:
            return None

        defn = next((d for d in DOMAIN_DEFINITIONS if d["id"] == domain_id), None)
        domain_title = defn["title"] if defn else domain_id.replace("_", " ").title()

        prev_q = questions[found_idx - 1] if found_idx > 0 else None
        next_q = questions[found_idx + 1] if found_idx < len(questions) - 1 else None

        source_obj = found.get("source")
        if not source_obj or not isinstance(source_obj, dict):
            source_obj = {
                "repository_name": found.get("source_repository", "").split("/")[-1] or "Source Repository",
                "repository_url": found.get("source_repository", defn["source_url"] if defn else ""),
                "source_path": found.get("source_file", ""),
                "commit_hash": found.get("source_commit", ""),
                "license_name": found.get("source_license", "Public Open Source"),
                "license_notice": found.get("translation_notice") or "Grounded in source repository.",
                "imported_at": found.get("imported_at", "2026-09-18T16:00:00Z"),
            }

        md_content = found.get("markdown_content") or found.get("content", "")
        diag = found.get("educational_diagram")
        if diag and diag not in md_content:
            alt = found.get("educational_diagram_alt") or "Educational Architecture Diagram"
            md_content = f"![{alt}]({diag})\n\n" + md_content

        cat_name = found.get("category_name") or found.get("category", "Fundamentals")
        top_name = found.get("topic", "Core Concepts")

        prev_info = {"id": prev_q["id"], "title": prev_q["title"], "slug": prev_q["slug"]} if prev_q else None
        next_info = {"id": next_q["id"], "title": next_q["title"], "slug": next_q["slug"]} if next_q else None

        return InterviewQuestionDetail(
            id=found["id"],
            slug=found["slug"],
            domain_id=domain_id,
            domain_title=domain_title,
            category=cat_name,
            topic=top_name,
            title=found["title"],
            difficulty=found.get("difficulty", "Intermediate"),
            experience_level=found.get("experience_level", "Mid-Level Engineer"),
            target_roles=found.get("target_roles", []),
            markdown_content=md_content,
            estimated_read_time_min=max(2, len(md_content.split()) // 150),
            has_code="```" in md_content,
            has_diagram=("![" in md_content) or bool(diag),
            tags=found.get("tags", []),
            source=source_obj,
            educational_diagram=found.get("educational_diagram"),
            educational_diagram_alt=found.get("educational_diagram_alt"),
            previous_question=prev_info,
            next_question=next_info,
        )

    def search_questions(self, query: str, domain_id: Optional[str] = None) -> List[InterviewQuestionSummary]:
        """Performs fast keyword search across question titles, categories, tags, and content."""
        q_lower = query.lower().strip()
        results: List[InterviewQuestionSummary] = []

        domains_to_search = [domain_id] if domain_id else [d["id"] for d in DOMAIN_DEFINITIONS]
        for d_id in domains_to_search:
            for q in self._load_domain_questions(d_id):
                score = 0
                title_lower = q.get("title", "").lower()
                slug_lower = q.get("slug", "").lower()
                tags = [t.lower() for t in q.get("tags", [])]
                content_lower = (q.get("markdown_content") or q.get("content") or "").lower()
                cat_val = q.get("category_name") or q.get("category", "Fundamentals")
                top_val = q.get("topic", "Core Concepts")

                if q_lower in title_lower or q_lower in slug_lower:
                    score += 10
                if any(q_lower in t for t in tags):
                    score += 5
                if q_lower in cat_val.lower() or q_lower in top_val.lower():
                    score += 3
                if q_lower in content_lower:
                    score += 1

                if score > 0:
                    results.append(
                        InterviewQuestionSummary(
                            id=q["id"],
                            slug=q["slug"],
                            title=q["title"],
                            category=cat_val,
                            topic=top_val,
                            difficulty=q.get("difficulty", "Intermediate"),
                            experience_level=q.get("experience_level", "Mid-Level Engineer"),
                            target_roles=q.get("target_roles", []),
                            estimated_read_time_min=q.get("estimated_read_time_min", 3),
                            has_code="```" in content_lower,
                            has_diagram=("![" in content_lower) or bool(q.get("educational_diagram")),
                        )
                    )

        return results

    def _build_smart_explanation_fields(self, q: InterviewQuestionDetail) -> Dict[str, Any]:
        title = q.title.lower()
        cat = q.category.lower()

        scenario = ""
        code = None
        takeaways = []

        if "social engineering" in title or "phishing" in title or "vishing" in title or "impersonation" in title:
            scenario = (
                "Case Scenario — Enterprise Vishing & Credential Harvester:\n\n"
                "• Actor 1 (Victim): Alice, a customer support representative at Apex Retail LLC.\n"
                "• Actor 2 (Attacker): Bob, an external adversary executing a targeted spear-phishing campaign.\n\n"
                "1. Reconnaissance: Bob reviews LinkedIn to discover Alice's department, her manager's name (David), and the company's SSO provider (Okta).\n"
                "2. The Call: Bob spoofs the internal company IT helpline number and calls Alice: 'Hi Alice, this is Bob from Apex Enterprise IT. We detected anomalous login attempts from Russia on your workstation. We need you to verify your identity immediately before your account gets locked out.'\n"
                "3. The Trap: Bob sends Alice an SMS containing a link: 'https://apexretail-sso-verify.com'. The landing page is a pixel-perfect replica of the internal Okta login portal.\n"
                "4. Exploitation: Alice enters her username, password, and SMS OTP. Bob's automated backend captures these credentials in real-time, logs into the real internal network, and establishes persistence.\n"
                "5. The Defense: Had Apex Retail deployed FIDO2 / WebAuthn hardware security keys (like YubiKey), the cryptographic challenge would have failed because the browser origin ('apexretail-sso-verify.com') does not match the genuine corporate domain, rendering Bob's phishing portal completely ineffective!"
            )
            code = (
                "# FIDO2 / WebAuthn Origin Verification Check (Python / FastWebAuthn):\n"
                "from webauthn import verify_authentication_response\n\n"
                "verification = verify_authentication_response(\n"
                "    credential=auth_credential,\n"
                "    expected_challenge=session['auth_challenge'],\n"
                "    expected_origin='https://sso.apexretail.com',  # Cryptographically rejects fake phishing domains!\n"
                "    expected_rp_id='apexretail.com',\n"
                "    credential_public_key=user.public_key,\n"
                "    credential_current_sign_count=user.sign_count,\n"
                ")\n"
                "assert verification.verified is True"
            )
            takeaways = [
                "Technical controls: Enforce FIDO2/WebAuthn hardware keys to make credential phishing mathematically impossible.",
                "Process controls: Enforce mandatory out-of-band verification procedures for any urgent internal credential requests.",
                "Human controls: Conduct frequent, realistic simulated phishing assessments coupled with blameless reporting channels."
            ]
        elif "sql" in title or "injection" in title:
            scenario = (
                "Case Scenario — SQL Injection & Admin Takeover:\n\n"
                "• Actor 1 (Developer): Alice, a backend engineer building an e-commerce inventory portal for BookNova.\n"
                "• Actor 2 (Attacker): Bob, an external researcher testing user input sanitization.\n\n"
                "1. Vulnerable Code: Alice constructed the user authentication query using raw string interpolation:\n"
                "   `f\"SELECT id, role, email FROM users WHERE email='{user_input}' AND password='{hashed_pw}'\"`\n"
                "2. The Attack: In the login email field, Bob submits: `' OR '1'='1' --`.\n"
                "3. Parser Hijacking: The database evaluates: `SELECT id, role, email FROM users WHERE email='' OR '1'='1' -- ...`. The condition `'1'='1'` evaluates to true for every row in the database, and `--` comments out the password check!\n"
                "4. Compromise: The database returns the very first row—the SuperAdmin account. Bob gains full administrative access with zero credentials.\n"
                "5. The Defense: Alice switches to parameterized queries with bind variables. The database driver treats Bob's input purely as literal string data, not executable SQL commands."
            )
            code = (
                "# Secure Parameterized Query (Python DB-API / SQLAlchemy):\n"
                "from sqlalchemy import text\n\n"
                "# SAFE: Values passed via parameter dictionary are never evaluated as SQL syntax\n"
                "query = text(\"SELECT id, role, email FROM users WHERE email = :email AND status = :status\")\n"
                "result = db.execute(query, {'email': untrusted_user_input, 'status': 'active'}).fetchone()\n"
                "# The database engine compiles the query plan before binding the parameter data."
            )
            takeaways = [
                "Never concatenate raw user input into SQL query strings (no f-strings, `%` formatters, or `+`).",
                "Use parameterized queries, ORM query builders, or stored procedures with bind parameters.",
                "Enforce database account least privilege: application services should never connect as DB superuser/root."
            ]
        elif "oauth" in title or "pkce" in title or "2fa" in title or "jwt" in title or "auth" in title:
            scenario = (
                "Case Scenario — Mobile App Auth & Code Interception Attack:\n\n"
                "• Actor 1 (User): Alice, using a single-page mobile banking app (FinMobile).\n"
                "• Actor 2 (Attacker): Bob, author of a malicious sideloaded background app (SpyUtility).\n\n"
                "1. Without PKCE: FinMobile initiates OAuth 2.0 authorization code flow via mobile browser. After Alice logs in, the browser redirects to FinMobile's custom URI: `finmobile://oauth-callback?code=AUTH_CODE_123`.\n"
                "2. Interception: Bob's malicious app SpyUtility has registered the identical custom URI scheme (`finmobile://`) on Android. The OS prompts or routes the intent to SpyUtility, allowing Bob to steal `AUTH_CODE_123`.\n"
                "3. With PKCE: Before opening the browser, FinMobile generates a high-entropy random string `code_verifier` and computes its SHA-256 hash `code_challenge`. Only the hash is sent in the initial request.\n"
                "4. Token Exchange: Even though Bob intercepts the authorization code, when Bob tries to exchange it for an access token at `/oauth/token`, the server demands the plaintext `code_verifier`. Because only FinMobile holds the secret `code_verifier`, Bob's token request is rejected!"
            )
            code = (
                "# Python RFC 7636 PKCE Implementation:\n"
                "import hashlib, base64, secrets\n\n"
                "# 1. Client creates unguessable secret verifier:\n"
                "code_verifier = secrets.token_urlsafe(64)\n\n"
                "# 2. Client hashes it to produce the challenge for authorization request:\n"
                "challenge_bytes = hashlib.sha256(code_verifier.encode('ascii')).digest()\n"
                "code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('ascii').rstrip('=')\n\n"
                "print(f'Safe Challenge: {code_challenge}\\nSecret Verifier: {code_verifier[:25]}...')"
            )
            takeaways = [
                "Public clients (SPAs, mobile apps) cannot safely store a static client_secret.",
                "PKCE dynamically generates a cryptographic one-time verifier/challenge pair per authorization request.",
                "Authorization code interception attacks are completely neutralized."
            ]
        elif "attention" in title or "transformer" in title or "qkv" in title or "llm" in title:
            scenario = (
                "Case Scenario — Resolving Long-Distance Semantic Ambiguity:\n\n"
                "• Actor 1 (Engineer): Alice, designing an enterprise document extraction LLM for legal contracts.\n"
                "• Context: A 200-word clause containing: 'The corporate borrower agreed to transfer collateral to the lender, provided it maintained audited solvency.'\n\n"
                "1. The Problem: What does 'it' refer to—the borrower, the collateral, or the lender? Traditional RNNs and LSTMs suffer from vanishing gradients and recency bias, losing the subject over 40 intermediate tokens.\n"
                "2. Self-Attention Mechanics: When processing the token 'it':\n"
                "   • Query ($Q$): 'What entity requires audited solvency?'\n"
                "   • Keys ($K$): Tokens like 'borrower', 'collateral', 'lender' broadcast their semantic properties.\n"
                "   • Scaled Dot-Product: The dot-product $Q \\cdot K^T$ between 'it' and 'borrower' yields a significantly higher score than with 'collateral'.\n"
                "3. Outcome: Softmax transforms this score into an attention weight of 0.82. The Value ($V$) representation of 'borrower' is directly merged into 'it', giving the model instant, accurate semantic disambiguation."
            )
            code = (
                "# PyTorch Scaled Dot-Product Attention Implementation:\n"
                "import torch\n"
                "import torch.nn.functional as F\n\n"
                "def scaled_dot_product_attention(Q, K, V, mask=None):\n"
                "    d_k = Q.size(-1)\n"
                "    # Pairwise similarity scaled by sqrt(d_k) to prevent softmax vanishing gradients\n"
                "    scores = torch.matmul(Q, K.transpose(-2, -1)) / (d_k ** 0.5)\n"
                "    if mask is not None:\n"
                "        scores = scores.masked_fill(mask == 0, -1e9)\n"
                "    attention_weights = F.softmax(scores, dim=-1)\n"
                "    return torch.matmul(attention_weights, V), attention_weights"
            )
            takeaways = [
                "Dividing by sqrt(d_k) prevents the softmax function from saturating into regions with vanishing gradients.",
                "Self-attention allows O(1) sequential path length across the entire token sequence.",
                "Multi-head attention allows the model to jointly attend to information from different representation subspaces."
            ]
        elif "rag" in title or "chunk" in title or "retriev" in title or "vector" in title:
            scenario = (
                "Case Scenario — Enterprise Customer Knowledge Grounding:\n\n"
                "• Actor 1 (User): Alice, a cloud engineer asking an internal IT chatbot: 'How do I request a dedicated GPU node in cluster eu-west-3 under policy revision 2026.4?'\n"
                "• Actor 2 (System): An enterprise RAG architecture combining dense vector embeddings with sparse BM25 retrieval.\n\n"
                "1. Without RAG: A base LLM was trained on public data up to 2023. It has never seen internal policy 2026.4 and hallucinates nonexistent CLI commands.\n"
                "2. Query Ingestion: Alice's question is passed to an embedding model (producing a 1536-dimensional vector) and a BM25 tokenizer.\n"
                "3. Hybrid Retrieval: The vector database finds semantically similar paragraphs, while BM25 guarantees keyword matches for 'eu-west-3' and '2026.4'. Reciprocal Rank Fusion (RRF) reranks the top 3 chunks.\n"
                "4. Prompt Augmentation: The system injects the retrieved chunks into the LLM system prompt: 'Answer Alice's query solely using the verified documentation provided below.'\n"
                "5. Grounded Output: The LLM gives the exact internal Slack command (`/gpu-request --cluster eu-west-3`), complete with citation links, with 0% hallucination."
            )
            code = (
                "# Hybrid Search with Reciprocal Rank Fusion (RRF):\n"
                "def reciprocal_rank_fusion(dense_ranks, sparse_ranks, k=60):\n"
                "    \"\"\"Combines dense semantic vector rankings with BM25 keyword rankings.\"\"\"\n"
                "    combined_scores = {}\n"
                "    for doc_id, rank in dense_ranks.items():\n"
                "        combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (k + rank)\n"
                "    for doc_id, rank in sparse_ranks.items():\n"
                "        combined_scores[doc_id] = combined_scores.get(doc_id, 0.0) + 1.0 / (k + rank)\n"
                "    return sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)"
            )
            takeaways = [
                "RAG grounds generative models in proprietary or real-time context, preventing hallucinations.",
                "Hybrid search (BM25 lexical + dense vectors) provides superior recall over pure vector search.",
                "Rerankers act as high-precision cross-encoders on the top candidate chunks before LLM generation."
            ]
        elif "agent" in title or "mcp" in title or "tool" in title or "react" in title:
            scenario = (
                "Case Scenario — Autonomous SRE Incident Remediation Agent:\n\n"
                "• Actor 1 (On-Call SRE): Alice, who receives a P1 alert that API latency spiked to 4.2 seconds.\n"
                "• Actor 2 (AI Agent): An autonomous diagnostic agent equipped with Model Context Protocol (MCP) tools for Kubernetes, Prometheus, and GitHub.\n\n"
                "1. Goal Assignment: Alice commands the agent: 'Diagnose the latency spike in service checkout-api and identify the culprit commit.'\n"
                "2. Thought & Tool Calling (Turn 1): Agent decides to query Prometheus metrics. Tool Call: `prometheus.query(metric='http_requests_duration_seconds')`. Result: 504 Gateway Timeouts started at 14:15 UTC.\n"
                "3. Thought & Tool Calling (Turn 2): Agent checks deployments around 14:15. Tool Call: `github.list_deployments(repo='checkout-api', since='14:00')`. Result: PR #402 ('Add synchronous fraud verification call') deployed at 14:12 UTC.\n"
                "4. Observation & Action (Turn 3): The agent inspects the code of PR #402, identifies an unindexed Redis call, posts a full root-cause report to Slack channel `#sre-incidents`, and proposes a hotfix revert PR."
            )
            code = (
                "# Minimal ReAct (Reasoning + Acting) Autonomous Loop:\n"
                "def run_react_agent(user_objective, tool_registry, llm_engine, max_turns=6):\n"
                "    history = f'Objective: {user_objective}\\n'\n"
                "    for turn in range(max_turns):\n"
                "        thought, tool_name, tool_args = llm_engine.plan_next_action(history)\n"
                "        if tool_name == 'TERMINATE':\n"
                "            return tool_args['final_answer']\n"
                "        tool_result = tool_registry.execute(tool_name, tool_args)\n"
                "        history += f'Thought: {thought}\\nAction: {tool_name}({tool_args})\\nObservation: {tool_result}\\n'\n"
                "    return 'Task exceeded maximum operational budget.'"
            )
            takeaways = [
                "ReAct combines reasoning (planning) with acting (tool invocation) for multi-step goals.",
                "MCP standardizes tool discovery, execution schemas, and resource access across AI clients.",
                "Memory architectures (short-term buffer + long-term vector store) give agents conversational persistence."
            ]
        elif "arp" in title or "mitm" in title or "man-in-the-middle" in title or "eavesdrop" in title:
            scenario = (
                "Case Scenario — Public Wi-Fi ARP Spoofing & Session Hijacking:\n\n"
                "• Actor 1 (Victim): Alice, sitting in an airport lounge connected to open Wi-Fi 'Airport-Free-WiFi'.\n"
                "• Actor 2 (Attacker): Bob, sitting in the same lounge running network sniffing software.\n\n"
                "1. The Setup: Alice's laptop has IP 192.168.1.45; the gateway router is 192.168.1.1.\n"
                "2. The Attack: Bob sends gratuitous ARP replies to Alice stating: '192.168.1.1 is at [Bob's MAC address]'. Simultaneously, Bob sends ARP packets to the gateway stating: '192.168.1.45 is at [Bob's MAC address]'.\n"
                "3. Man-In-The-Middle: Alice's device updates its ARP table. Now, every single network packet Alice sends to the internet is directed to Bob's network card first before Bob forwards it to the router.\n"
                "4. Exploitation: If Alice visits legacy HTTP services or ignores browser TLS warnings, Bob captures her session cookies and plaintext passwords in real time.\n"
                "5. Defenses: Dynamic ARP Inspection (DAI) on switches, static ARP binding, and Alice using a full-tunnel VPN that encrypts all link-layer traffic inside IPsec or WireGuard."
            )
            code = (
                "# Inspecting and Hardening Local ARP Cache:\n"
                "# 1. Check current ARP table for duplicate MAC addresses (signature of ARP poisoning):\n"
                "arp -a\n\n"
                "# 2. Bind default gateway MAC address statically (Windows PowerShell Admin):\n"
                "netsh interface ipv4 add neighbors 'Wi-Fi' '192.168.1.1' '00-11-22-33-44-55'"
            )
            takeaways = [
                "Dynamic ARP Inspection (DAI) matches ARP packets against DHCP snooping binding databases.",
                "Always enforce TLS 1.3 with HSTS (HTTP Strict Transport Security) to prevent protocol downgrade.",
                "VPNs wrap all traffic in encrypted tunnels, rendering intercepted local packets useless to eavesdroppers."
            ]
        elif "firewall" in title or "vpn" in title or "dns" in title or "port" in title or "network" in cat:
            scenario = (
                "Case Scenario — Ingress Filtering & Remote Worker Tunneling:\n\n"
                "• Actor 1 (Remote Engineer): Alice, working from home needing access to a production database cluster (10.0.5.20).\n"
                "• Actor 2 (Attacker): Bob, scanning internet IP ranges looking for exposed port 3306 or 5432.\n\n"
                "1. The Risk: If BookNova opens database ports directly to `0.0.0.0/0`, Bob launches brute-force dictionary attacks against database credentials.\n"
                "2. Network Security Architecture: The company edge firewall blocks all incoming internet traffic to port 3306/5432 (`DROP`).\n"
                "3. The Secure Path: Alice initiates a VPN tunnel (using WireGuard/TLS). Alice authenticates with MFA and device health attestation.\n"
                "4. The Result: The firewall validates Alice's encrypted tunnel, maps her onto the authorized internal subnet (10.0.10.x), and permits traffic to 10.0.5.20 while Bob's external probes are completely rejected."
            )
            code = (
                "# Linux nftables / iptables Stateful Ingress Protection:\n"
                "# Allow established connections, permit internal admin VPN, drop everything else:\n"
                "iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT\n"
                "iptables -A INPUT -p tcp --dport 22 -s 10.0.10.0/24 -j ACCEPT\n"
                "iptables -A INPUT -i wg0 -p tcp --dport 3306 -j ACCEPT\n"
                "iptables -P INPUT DROP"
            )
            takeaways = [
                "Stateful firewalls track connection state tables, permitting return traffic automatically.",
                "Defense-in-depth requires combining perimeter filtering with host-based controls and network segmentation.",
                "Always close or filter unused listening ports to minimize attack surface."
            ]
        else:
            scenario = (
                f"Case Scenario — Production Implementation of {q.title}:\n\n"
                f"• Actor 1 (Lead Engineer): Alice, tasked with implementing {q.title} within an enterprise production architecture.\n"
                f"• Actor 2 (Auditor / Adversary): Bob, evaluating the system for scalability bottlenecks and edge-case failure modes.\n\n"
                f"1. Operational Reality: When deployed in production, {q.topic} directly influences system resilience, performance, and security boundaries.\n"
                f"2. The Challenge: Alice must account for unexpected failure conditions, network partitions, and resource constraints.\n"
                f"3. Practical Solution: Alice establishes telemetry, enforces least privilege access, and writes automated tests to validate behavior under load."
            )
            takeaways = [
                f"Clarify system requirements, scale parameters, and trust boundaries before answering {q.topic}.",
                "Highlight both theoretical advantages and operational pitfalls or failure modes.",
                "Frame your answer with a concrete engineering project or production incident from your career."
            ]

        return {
            "real_world_scenario": scenario,
            "code_sample": code,
            "key_interview_takeaways": takeaways,
        }

    def _load_few_shot_fixture(self, domain_id: str, lang: str = "en") -> Optional[dict]:
        """Loads versioned few-shot structured exemplars for prompt grounding."""
        try:
            fixture_file = self.content_root / "fixtures" / "explain_fixtures.json"
            if fixture_file.exists():
                with open(fixture_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang_data = data.get(lang) or data.get("en") or {}
                    return lang_data.get(domain_id) or lang_data.get("security_engineering")
        except Exception as e:
            logger.warning(f"Could not load explain fixture: {e}")
        return None

    def _build_structured_fallback_payload(self, q: InterviewQuestionDetail, lang: str = "en") -> StructuredAIExplanationPayload:
        """
        Builds a deterministic, schema-validated StructuredAIExplanationPayload.
        Used when AI is offline, slow, or fails validation.
        """
        slug = (q.slug or "").lower()
        title = (q.title or "").lower()
        fixture_data = self._load_few_shot_fixture(q.domain_id, lang)

        # 1. Domain-specific exact fixture matches (2FA, OAuth, Spark, RAG)
        if ("2fa" in slug or "two-factor" in slug or "authenticat" in slug) and fixture_data and "2fa" in str(fixture_data).lower():
            try:
                payload = StructuredAIExplanationPayload(**fixture_data)
                if not payload.svg_diagram and should_question_have_diagram(q):
                    from ..scraper.sanitizer import sanitize_svg
                    raw_svg = _generate_question_svg_diagram(q)
                    payload.svg_diagram = sanitize_svg(raw_svg)
                    payload.has_diagram = bool(payload.svg_diagram)
                return payload
            except Exception:
                pass

        if ("broadcast" in slug or "spark" in slug or "shuffle" in slug) and fixture_data and "broadcast" in str(fixture_data).lower():
            try:
                payload = StructuredAIExplanationPayload(**fixture_data)
                if not payload.svg_diagram and should_question_have_diagram(q):
                    from ..scraper.sanitizer import sanitize_svg
                    raw_svg = _generate_question_svg_diagram(q)
                    payload.svg_diagram = sanitize_svg(raw_svg)
                    payload.has_diagram = bool(payload.svg_diagram)
                return payload
            except Exception:
                pass

        if ("rag" in slug or "vector" in slug or "retriev" in slug) and fixture_data and "rag" in str(fixture_data).lower():
            try:
                payload = StructuredAIExplanationPayload(**fixture_data)
                if not payload.svg_diagram and should_question_have_diagram(q):
                    from ..scraper.sanitizer import sanitize_svg
                    raw_svg = _generate_question_svg_diagram(q)
                    payload.svg_diagram = sanitize_svg(raw_svg)
                    payload.has_diagram = bool(payload.svg_diagram)
                return payload
            except Exception:
                pass

        # 2. Universal structured fallback guaranteed to be schema-compliant
        summary = f"{q.title} defines foundational architectural mechanics in {q.category}."
        if q.markdown_content:
            first_sent = q.markdown_content.split(".")[0].replace("#", "").strip()
            if len(first_sent) > 20:
                summary = first_sent[:180] + "."

        analogy = f"Like establishing an automated checkpoint that validates constraints before allowing high-concurrency operations."
        if "sql" in title or "database" in title:
            analogy = "Like checking an ID at a club entrance instead of letting anyone in and checking them on the dance floor."
        elif "firewall" in title or "network" in title:
            analogy = "Like a secured gated community where uninvited external cars are stopped at the perimeter gate."
        elif "attention" in title or "transformer" in title:
            analogy = "Like highlighting critical keywords in a 100-page book with colored markers to see connections across chapters."

        actors = [
            Actor(id="alice", role="legitimate_user", label="Alice", description="Client or employee initiating operations"),
            Actor(id="system", role="system", label="Target System", description=f"Core service processing {q.topic}"),
            Actor(id="bob", role="attacker", label="Bob", description="External client, adversary, or auditor"),
        ]

        variant_failure = ScenarioVariant(
            label="Without Recommended Architecture (Naive / Unprotected)",
            outcome="failure",
            steps=[
                ScenarioStep(order=1, from_actor="alice", to_actor="system", action="Dispatches request without safeguards or tuning", payload="req_data", annotation="Initial request", status="normal"),
                ScenarioStep(order=2, from_actor="bob", to_actor="system", action="Exposes bottleneck, race condition, or vulnerability", payload="exploit / probe", annotation="Bottleneck exposed", status="attack"),
                ScenarioStep(order=3, from_actor="system", to_actor="alice", action="Drops transaction due to contention or policy violation", payload="HTTP 500 / Timeout", annotation="System failure", status="blocked"),
            ]
        )

        variant_success = ScenarioVariant(
            label="With Production Architecture (Optimized / Hardened)",
            outcome="success",
            steps=[
                ScenarioStep(order=1, from_actor="alice", to_actor="system", action="Dispatches authenticated and structured request", payload="signed_req", annotation="Validated input", status="normal"),
                ScenarioStep(order=2, from_actor="system", to_actor="system", action="Executes stateful validation or in-memory cache lookup", payload="cached_lookup", annotation="Zero-overhead path", status="secure"),
                ScenarioStep(order=3, from_actor="system", to_actor="alice", action="Returns verified low-latency response", payload="HTTP 200 OK", annotation="Production success", status="secure"),
            ]
        )

        scenario = Scenario(
            title=f"Case Scenario — Production Execution Flow: {q.title[:60]}",
            variants=[variant_failure, variant_success]
        )

        code_sample = None
        if q.has_code or "security" in q.domain_id or "data" in q.domain_id or "phish" in slug or "social" in slug:
            code_sample = CodeSample(
                language="python",
                code=f"# Verified defensive/implementation pattern for {q.topic}\ndef enforce_guardrails(request_payload):\n    validated = validate_security_constraints(request_payload)\n    if not validated:\n        raise ValueError('Blocked unauthorized or malformed transaction')\n    return execute_production_pipeline(validated)",
                explanation_lines=[
                    CodeExplanationLine(line=3, note="Validates input constraints prior to execution"),
                    CodeExplanationLine(line=5, note="Blocks malformed or suspicious payloads")
                ]
            )

        comparison_table = [
            ComparisonRow(criterion="Performance / Latency", option_a="Naive: High latency and potential resource starvation", option_b="Production: Deterministic sub-millisecond execution"),
            ComparisonRow(criterion="Failure Boundary", option_a="Naive: Cascading failures under unexpected load", option_b="Production: Isolated blast radius with graceful degradation"),
            ComparisonRow(criterion="Operational Complexity", option_a="Naive: Simple initial setup but high incident rate", option_b="Production: Requires initial design but maintenance is low")
        ]

        takeaways = [
            f"Articulate both the core theory and practical trade-offs of {q.topic}.",
            "Highlight failure modes (e.g. latency, race conditions, security vectors) to prove production experience.",
            "Cite a concrete project from your career where this decision impacted latency or reliability."
        ]

        common_mistakes = [
            "Giving a purely textbook definition without mentioning operational edge cases.",
            "Ignoring scalability limits when traffic surges 10x.",
            "Forgetting to address observability, logging, and metrics."
        ]

        # Determine diagram requirement & sanitize
        has_diag = should_question_have_diagram(q)
        clean_svg = None
        if has_diag:
            from ..scraper.sanitizer import sanitize_svg
            raw_svg = _generate_question_svg_diagram(q)
            clean_svg = sanitize_svg(raw_svg)
            has_diag = bool(clean_svg)

        return StructuredAIExplanationPayload(
            concept_summary=summary,
            analogy=analogy,
            actors=actors,
            scenario=scenario,
            code_sample=code_sample,
            comparison_table=comparison_table,
            takeaways=takeaways,
            common_mistakes=common_mistakes,
            has_diagram=has_diag,
            svg_diagram=clean_svg,
        )

    async def explain_with_ai(
        self,
        domain_id: str,
        question_slug: str,
        mode: str = "simplify",
        user_draft_answer: Optional[str] = None,
        language: str = "en",
        force_regenerate: bool = False,
    ) -> QuestionAIExplainResponse:
        """
        Generates or retrieves a structured, visual-ready explanation for a question.
        Returns strict JSON adhering to StructuredAIExplanationPayload.
        Caches results per (question_id, language, model_name, schema_version).
        """
        q = self.get_question_detail(domain_id, question_slug)
        if not q:
            return QuestionAIExplainResponse(
                question_id=f"{domain_id}-{question_slug}",
                mode=mode,
                explanation="Question not found.",
                ai_model_used="none",
            )

        lang = (language or "en").lower().strip()
        if lang not in ["en", "fr", "de"]:
            lang = "en"

        from .ai_gateway import get_active_provider, get_selected_model
        _active_prov = get_active_provider()
        _active_model = get_selected_model(_active_prov)
        # Cache key includes provider so Gemini/OpenAI/Ollama answers are stored separately
        model_key = f"{_active_prov.value}:{_active_model or 'default'}"
        SCHEMA_VERSION = 2

        # 1. Database Cache Check (skip if user explicitly requested regenerate)
        if not force_regenerate:
            try:
                with SessionLocal() as db:
                    cached = db.query(InterviewExplanation).filter(
                        InterviewExplanation.question_id == q.id,
                        InterviewExplanation.language == lang,
                        InterviewExplanation.model_name.in_([model_key, "deterministic-smart-ai"]),
                        InterviewExplanation.schema_version == SCHEMA_VERSION,
                    ).order_by(InterviewExplanation.id.desc()).first()
                    if cached and cached.payload:
                        try:
                            structured_payload = StructuredAIExplanationPayload(**cached.payload)
                            actor_names = " vs ".join(a.label for a in structured_payload.actors)
                            return QuestionAIExplainResponse(
                                question_id=q.id,
                                mode=mode,
                                explanation=structured_payload.concept_summary,
                                real_world_scenario=f"Case Scenario — {structured_payload.scenario.title} ({actor_names})",
                                code_sample=structured_payload.code_sample.code if structured_payload.code_sample else None,
                                key_interview_takeaways=structured_payload.takeaways,
                                structured_payload=structured_payload,
                                ai_model_used=cached.model_name or model_key,
                                has_diagram=structured_payload.has_diagram,
                                svg_diagram=structured_payload.svg_diagram,
                            )
                        except Exception as e:
                            logger.warning(f"Cached explanation payload failed validation: {e}")
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

        # 2. AI Gateway Generation Attempt (Ollama, Gemini, OpenAI)
        structured_payload: Optional[StructuredAIExplanationPayload] = None
        model_used = model_key

        few_shot = self._load_few_shot_fixture(domain_id, lang)
        few_shot_str = json.dumps(few_shot, indent=2) if few_shot else "{}"

        prompt = (
            "You are an expert technical interviewer and systems architect.\n"
            f"Explain the technical interview question below in {lang.upper()}.\n"
            "Return ONLY a valid JSON object matching the StructuredAIExplanationPayload schema.\n"
            "DO NOT output markdown code fences like ```json or conversational prose. Return raw valid JSON only.\n\n"
            f"Question Title: {q.title}\n"
            f"Category: {q.category} ({q.topic})\n"
            f"Source Technical Context: {q.markdown_content[:700]}\n\n"
            "Required Output Structure:\n"
            "1. concept_summary: A simplified, plain-language restatement of the concept (explain clearly as to a colleague).\n"
            "2. analogy: A practical real-world analogy grounded in everyday life (use appropriate emoji like 🏢, 🛡️, ⚙️, 🚀 for approachable clarity).\n"
            "3. actors: List 2-4 key architectural actors (id, role, label, description).\n"
            "4. scenario: Case scenario with title and 2 variants: 'Without Recommended Architecture (Naive / Unprotected)' and 'With Production Architecture (Optimized / Hardened)'. Each step's 'from' and 'to' must match declared actor ids.\n"
            "5. code_sample: Concise production code sample with 1-3 explanation lines (or null if purely theoretical).\n"
            "6. comparison_table: 2-3 comparison rows evaluating trade-offs (criterion, option_a, option_b).\n"
            "7. takeaways: 3 practical talking points for interviews.\n"
            "8. common_mistakes: 2-3 traps or misconceptions to avoid.\n"
            "9. has_diagram: boolean. Set to true if an architecture, flow, or sequence diagram genuinely clarifies this concept; false for purely definitional questions.\n"
            "10. svg_diagram: string or null. If has_diagram is true, provide clean, valid standalone SVG markup with viewBox '0 0 640 200' using only visual elements (<svg>, <rect>, <circle>, <path>, <line>, <text>, <g>, <defs>, <marker>). DO NOT include <script>, <foreignObject>, <iframe>, or external URLs. If has_diagram is false, set to null.\n\n"
            "Few-Shot Exemplar Structure Reference:\n"
            f"{few_shot_str}\n"
        )

        try:
            from .ai_gateway import generate_completion
            from ..scraper.sanitizer import sanitize_svg

            raw_resp = generate_completion(
                prompt=prompt,
                model=_active_model,
                provider=_active_prov,
                response_json=True,
                temperature=0.2,
                timeout_seconds=40.0,
            )
            if raw_resp:
                clean_json = raw_resp.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                try:
                    parsed_dict = json.loads(clean_json)

                    # Sanitize any SVG diagram produced by the model
                    if parsed_dict.get("svg_diagram"):
                        clean_svg = sanitize_svg(parsed_dict["svg_diagram"])
                        parsed_dict["svg_diagram"] = clean_svg
                        parsed_dict["has_diagram"] = bool(clean_svg)
                    else:
                        parsed_dict["svg_diagram"] = None
                        parsed_dict["has_diagram"] = False

                    # If model didn't generate SVG but concept genuinely needs one, provide tailored visual
                    if not parsed_dict.get("svg_diagram") and should_question_have_diagram(q):
                        fallback_svg = _generate_question_svg_diagram(q)
                        clean_svg = sanitize_svg(fallback_svg)
                        parsed_dict["svg_diagram"] = clean_svg
                        parsed_dict["has_diagram"] = bool(clean_svg)

                    structured_payload = StructuredAIExplanationPayload(**parsed_dict)
                    model_used = model_key
                except Exception as parse_err:
                    logger.warning(f"Model JSON failed validation: {parse_err}. Attempting repair retry...")
                    repair_prompt = (
                        f"The previous output had a validation error: {parse_err}.\n"
                        "Fix the JSON so all steps[].from and steps[].to match a declared actors[].id.\n"
                        f"Original question: {q.title}\n"
                        "Return ONLY the fixed raw JSON."
                    )
                    repair_resp = generate_completion(
                        prompt=repair_prompt,
                        model=_active_model,
                        provider=_active_prov,
                        response_json=True,
                        temperature=0.1,
                        timeout_seconds=35.0,
                    )
                    if repair_resp:
                        repair_text = repair_resp.strip()
                        if repair_text.startswith("```json"):
                            repair_text = repair_text[7:]
                        if repair_text.endswith("```"):
                            repair_text = repair_text[:-3]
                        repair_dict = json.loads(repair_text.strip())

                        if repair_dict.get("svg_diagram"):
                            clean_svg = sanitize_svg(repair_dict["svg_diagram"])
                            repair_dict["svg_diagram"] = clean_svg
                            repair_dict["has_diagram"] = bool(clean_svg)
                        elif should_question_have_diagram(q):
                            fallback_svg = _generate_question_svg_diagram(q)
                            clean_svg = sanitize_svg(fallback_svg)
                            repair_dict["svg_diagram"] = clean_svg
                            repair_dict["has_diagram"] = bool(clean_svg)

                        structured_payload = StructuredAIExplanationPayload(**repair_dict)
                        model_used = model_key
        except Exception as exc:
            logger.info(f"AI gateway generation unavailable ({exc}). Using deterministic structured fallback.")

        # 3. Deterministic fallback if AI was offline or failed schema
        if not structured_payload:
            structured_payload = self._build_structured_fallback_payload(q, lang)
            model_used = "deterministic-smart-ai"

        # 4. Cache in Database
        try:
            with SessionLocal() as db:
                existing = db.query(InterviewExplanation).filter(
                    InterviewExplanation.question_id == q.id,
                    InterviewExplanation.language == lang,
                    InterviewExplanation.model_name == model_used,
                    InterviewExplanation.schema_version == SCHEMA_VERSION,
                ).first()
                if existing:
                    existing.payload = structured_payload.model_dump(by_alias=True)
                    existing.generated_at = datetime.utcnow()
                else:
                    new_cache = InterviewExplanation(
                        question_id=q.id,
                        language=lang,
                        model_name=model_used,
                        payload=structured_payload.model_dump(by_alias=True),
                        schema_version=SCHEMA_VERSION,
                        generated_at=datetime.utcnow(),
                    )
                    db.add(new_cache)
                db.commit()
        except Exception as cache_err:
            logger.warning(f"Failed to persist explanation to cache: {cache_err}")

        actor_names = " vs ".join(a.label for a in structured_payload.actors)
        return QuestionAIExplainResponse(
            question_id=q.id,
            mode=mode,
            explanation=structured_payload.concept_summary,
            real_world_scenario=f"Case Scenario — {structured_payload.scenario.title} ({actor_names})",
            code_sample=structured_payload.code_sample.code if structured_payload.code_sample else None,
            key_interview_takeaways=structured_payload.takeaways,
            structured_payload=structured_payload,
            ai_model_used=model_used,
            has_diagram=structured_payload.has_diagram,
            svg_diagram=structured_payload.svg_diagram,
        )

    def evaluate_star_draft(
        self,
        draft_answer: str,
        question_title: Optional[str] = None,
        language: str = "en",
    ) -> STAREvaluationResponse:
        """
        Evaluates a candidate's draft STAR behavioral response using deterministic heuristics.
        Analyzes coverage, quantified metrics, and 'I' vs 'We' ownership ratio.
        """
        text = (draft_answer or "").strip()
        words = text.split()
        total_words = len(words)
        text_lower = text.lower()

        # 1. STAR Coverage detection
        has_s = any(k in text_lower for k in [
            "situation", "context", "when i", "at my", "in my role", "working at",
            "lorsque", "dans mon", "contexte", "en tant que",
            "als ich", "bei meinem", "in meiner rolle"
        ])
        has_t = any(k in text_lower for k in [
            "task", "tasked with", "responsibility", "objective", "goal", "sla", "deadline", "mission",
            "objectif", "responsabilité", "défi",
            "aufgabe", "ziel", "verantwortung"
        ])
        has_a = any(k in text_lower for k in [
            "action", "i designed", "i built", "i implemented", "i profiled", "i refactored", "i decided", "i resolved",
            "j'ai", "je conçu", "j'ai implémenté", "j'ai analysé", "j'ai décidé",
            "ich entwickelte", "ich implementierte", "ich entschied", "ich analysierte"
        ])
        has_r = any(k in text_lower for k in [
            "result", "reduced", "increased", "saved", "latency", "throughput", "impact", "delivered",
            "résultat", "réduit", "augmenté", "économisé", "latence",
            "ergebnis", "gesenkt", "gesteigert", "eingespart", "latenz"
        ])

        # 2. Action proportion estimate (Target: 60%)
        est_action_prop = 60 if (has_a and total_words > 40) else (35 if has_a else 15)

        # 3. Quantified metrics detection
        metric_patterns = [
            r"\b\d+%\b",                                    # percentages
            r"\b\d+\s*(?:ms|s|sec|seconds|minutes)\b",      # latencies
            r"\b(?:\$|€|£|\d+\s*(?:usd|eur|mad))\b",        # currency
            r"\b\d+\s*(?:req/s|rps|qps|gb|tb|mb|k)\b",      # volume/rates
            r"\b\d+\b",                                     # raw digits
        ]
        detected_metrics = []
        for pat in metric_patterns:
            matches = re.findall(pat, text_lower)
            for m in matches[:3]:
                if m not in detected_metrics:
                    detected_metrics.append(m)

        metrics_score = min(10, len(detected_metrics) * 3)

        # 4. Ownership ratio (I vs We)
        i_tokens = re.findall(r"\b(i|my|me|mine|j'ai|je|mon|ma|mes|moi|ich|mein|mir|mich)\b", text_lower)
        we_tokens = re.findall(r"\b(we|our|us|ours|nous|notre|nos|wir|unser|uns)\b", text_lower)
        i_count = len(i_tokens)
        we_count = len(we_tokens)
        total_ownership = i_count + we_count
        i_percentage = round((i_count / total_ownership) * 100, 1) if total_ownership > 0 else 0.0

        strengths = []
        missing = []
        recommendations = []

        if has_s and has_t and has_a and has_r:
            strengths.append("Complete STAR structure: All four phases (Situation, Task, Action, Result) detected.")
        else:
            if not has_s:
                missing.append("Situation: Set the scene and scale constraints in under 45 seconds.")
            if not has_t:
                missing.append("Task: Specify your individual ownership and explicit success criteria.")
            if not has_a:
                missing.append("Action (60%): Detail the architectural trade-offs and technical decisions YOU executed.")
            if not has_r:
                missing.append("Result: Conclude with quantified business, performance, or team velocity impact.")

        if metrics_score >= 6:
            strengths.append(f"Strong quantification: {len(detected_metrics)} measurable data points detected ({', '.join(detected_metrics[:3])}).")
        else:
            recommendations.append("Quantify your result: add specific numbers (e.g. 'reduced latency by 45%', 'saved $40k/yr', 'zero dropped transactions').")

        if i_percentage >= 60:
            strengths.append(f"High personal ownership ({i_percentage}% 'I' statements): hiring managers can clearly see your individual contribution.")
        elif we_count > i_count:
            recommendations.append(f"Excessive team passive language detected ('we' used {we_count} times vs 'I' {i_count} times). Reframe around actions YOU personally drove.")

        return STAREvaluationResponse(
            star_coverage={"situation": has_s, "task": has_t, "action": has_a, "result": has_r},
            action_proportion_estimate=est_action_prop,
            quantified_metrics_score=metrics_score,
            metrics_detected=detected_metrics,
            ownership_ratio={"i_count": i_count, "we_count": we_count, "i_percentage": i_percentage},
            strengths=strengths,
            missing_elements=missing,
            recommendations=recommendations,
        )

    def _load_domain_questions(self, domain_id: str) -> List[Dict[str, Any]]:
        if domain_id in self._questions_cache:
            return self._questions_cache[domain_id]

        file_path = self.content_root / domain_id / "questions.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._questions_cache[domain_id] = data
                    return data
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")

        self._questions_cache[domain_id] = []
        return []

    def _load_domain_metadata(self, domain_id: str) -> Dict[str, Any]:
        if domain_id in self._metadata_cache:
            return self._metadata_cache[domain_id]

        file_path = self.content_root / domain_id / "metadata.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._metadata_cache[domain_id] = data
                    return data
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")

        self._metadata_cache[domain_id] = {}
        return {}


interview_prep_service = InterviewPrepService()
