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
    ExplainContextPack,
    PreExplanationContent,
    PreExplanationData,
    QuestionDeepDivePayload,
    QuestionExplanationResponse,
    QuestionDeepDiveRequest,
    QuestionDeepDiveResponse,
)
from ..config import get_settings
from ..database import SessionLocal
from ..models import InterviewExplanation

logger = logging.getLogger("compust.interview_prep.service")

SCHEMA_VERSION = 3
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


def _generate_question_svg_diagram(q: InterviewQuestionDetail, pack: Optional[ExplainContextPack] = None) -> Optional[str]:
    """
    Generates a clean, valid, professional SVG diagram specific to this question.
    Driven by the question's own pre-explanation or ExplainContextPack.
    Uses theme-aware currentColor and CSS variables for dark/light mode compatibility.
    """
    # 1. Check if pre-explanation carries authored static SVG
    try:
        pre_exp = interview_prep_service.load_raw_pre_explanation(q.domain_id, q.id or q.slug)
        if pre_exp and pre_exp.get("diagram_svg"):
            return pre_exp["diagram_svg"]
    except Exception:
        pass

    if pack and pack.diagram_type == "none":
        return None

    if not pack:
        diag_type = "flow"
        concepts = [
            html.escape((q.topic or "Topic")[:24]),
            "Ingest / Stage",
            "Process / Transform",
            "Store / Sink",
        ]
        escaped_brief = html.escape((q.title or "Architecture Overview")[:55])
    else:
        diag_type = pack.diagram_type
        raw_concepts = pack.key_concepts or []
        concepts = [html.escape(str(c)[:24]) for c in raw_concepts]
        while len(concepts) < 4:
            concepts.append(f"Component {len(concepts)+1}")
        escaped_brief = html.escape((pack.diagram_brief or "")[:55])

    c1, c2, c3, c4 = concepts[0], concepts[1], concepts[2], concepts[3]
    escaped_title = html.escape((q.title or "Technical Architecture")[:36])
    domain = (q.domain_id or "").lower()
    
    # Theme palette based on domain
    if "security" in domain:
        accent_color = "#38bdf8"
        gate_color = "#a78bfa"
        core_color = "#34d399"
        card_stroke = "#334155"
        category_label = "SECURITY ARCHITECTURE"
    elif "ai" in domain:
        accent_color = "#60a5fa"
        gate_color = "#c084fc"
        core_color = "#22d3ee"
        card_stroke = "#1e293b"
        category_label = "AI ARCHITECTURE & PIPELINE"
    else:
        accent_color = "#38bdf8"
        gate_color = "#fbbf24"
        core_color = "#34d399"
        card_stroke = "#334155"
        category_label = "DISTRIBUTED SYSTEMS TOPOLOGY"

    if diag_type == "flow":
        return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <marker id="arrowHead" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{accent_color}" />
    </marker>
    <marker id="arrowHeadGreen" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{core_color}" />
    </marker>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#flowGrad)" stroke="{card_stroke}" stroke-width="1.5" />
  <text x="20" y="26" fill="{accent_color}" font-size="10" font-weight="700" letter-spacing="1">{category_label}: {escaped_title.upper()}</text>
  {f'<text x="20" y="42" fill="#94a3b8" font-size="9">{escaped_brief}</text>' if escaped_brief else ''}

  <rect x="24" y="66" width="130" height="85" rx="8" fill="#1e293b" stroke="{accent_color}" stroke-width="1.5" />
  <text x="36" y="90" fill="{accent_color}" font-size="11" font-weight="700">1. Stage</text>
  <text x="36" y="112" fill="#f8fafc" font-size="11" font-weight="600">{c1}</text>
  <text x="36" y="130" fill="#94a3b8" font-size="9">Input &amp; Parsing</text>

  <line x1="154" y1="108" x2="182" y2="108" stroke="{accent_color}" stroke-width="2" marker-end="url(#arrowHead)" />

  <rect x="188" y="66" width="130" height="85" rx="8" fill="#1e293b" stroke="{gate_color}" stroke-width="1.5" />
  <text x="200" y="90" fill="{gate_color}" font-size="11" font-weight="700">2. Processing</text>
  <text x="200" y="112" fill="#f8fafc" font-size="11" font-weight="600">{c2}</text>
  <text x="200" y="130" fill="#94a3b8" font-size="9">Transformation Core</text>

  <line x1="318" y1="108" x2="346" y2="108" stroke="{gate_color}" stroke-width="2" marker-end="url(#arrowHead)" />

  <rect x="352" y="66" width="130" height="85" rx="8" fill="#1e293b" stroke="{core_color}" stroke-width="1.5" />
  <text x="364" y="90" fill="{core_color}" font-size="11" font-weight="700">3. Optimization</text>
  <text x="364" y="112" fill="#f8fafc" font-size="11" font-weight="600">{c3}</text>
  <text x="364" y="130" fill="#94a3b8" font-size="9">State &amp; Partitions</text>

  <line x1="482" y1="108" x2="506" y2="108" stroke="{core_color}" stroke-width="2" marker-end="url(#arrowHeadGreen)" />

  <rect x="512" y="66" width="104" height="85" rx="8" fill="#0f172a" stroke="{core_color}" stroke-width="1.5" />
  <text x="522" y="90" fill="{core_color}" font-size="11" font-weight="700">4. Target</text>
  <text x="522" y="112" fill="#f8fafc" font-size="10" font-weight="600">{c4}</text>
  <text x="522" y="130" fill="#94a3b8" font-size="9">Verified Output</text>
</svg>"""

    elif diag_type == "comparison":
        return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="compGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#compGrad)" stroke="{card_stroke}" stroke-width="1.5" />
  <text x="20" y="26" fill="{accent_color}" font-size="10" font-weight="700" letter-spacing="1">ARCHITECTURAL COMPARISON: {escaped_title.upper()}</text>
  {f'<text x="20" y="42" fill="#94a3b8" font-size="9">{escaped_brief}</text>' if escaped_brief else ''}

  <!-- Pattern A -->
  <rect x="24" y="60" width="280" height="115" rx="8" fill="#1e293b" stroke="#ef4444" stroke-width="1.5" />
  <text x="40" y="86" fill="#f87171" font-size="12" font-weight="700">Approach A (Baseline / Naive): {c1}</text>
  <text x="40" y="110" fill="#cbd5e1" font-size="10">• Latency profile: Higher compute / IO overhead</text>
  <text x="40" y="128" fill="#cbd5e1" font-size="10">• Failure mode: Unbounded resource contention</text>
  <text x="40" y="146" fill="#94a3b8" font-size="9">Operational limit: Bottleneck under burst load</text>

  <!-- VS Separator -->
  <text x="320" y="122" fill="#94a3b8" font-size="12" font-weight="bold" text-anchor="middle">VS</text>

  <!-- Pattern B -->
  <rect x="336" y="60" width="280" height="115" rx="8" fill="#1e293b" stroke="{core_color}" stroke-width="1.5" />
  <text x="352" y="86" fill="{core_color}" font-size="12" font-weight="700">Approach B (Engineered / Hardened): {c2}</text>
  <text x="352" y="110" fill="#cbd5e1" font-size="10">• Latency profile: Low-latency deterministic path</text>
  <text x="352" y="128" fill="#cbd5e1" font-size="10">• Scalability: Partitioned / cached execution</text>
  <text x="352" y="146" fill="#34d399" font-size="9">✓ Production grade: High availability &amp; throughput</text>
</svg>"""

    # architecture, sequence, or hierarchy
    return f"""<svg viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="archGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
    <marker id="archArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{accent_color}" />
    </marker>
    <marker id="archGreen" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="{core_color}" />
    </marker>
  </defs>
  <rect x="2" y="2" width="636" height="196" rx="10" fill="url(#archGrad)" stroke="{card_stroke}" stroke-width="1.5" />
  <text x="20" y="26" fill="{accent_color}" font-size="10" font-weight="700" letter-spacing="1">{category_label}: {escaped_title.upper()}</text>
  {f'<text x="20" y="42" fill="#94a3b8" font-size="9">{escaped_brief}</text>' if escaped_brief else ''}

  <!-- Tier 1: Client/Ingress -->
  <rect x="24" y="64" width="160" height="96" rx="8" fill="#1e293b" stroke="{accent_color}" stroke-width="1.5" />
  <text x="36" y="88" fill="{accent_color}" font-size="11" font-weight="700">Tier 1: Client / Ingress</text>
  <text x="36" y="112" fill="#f8fafc" font-size="11" font-weight="600">{c1}</text>
  <text x="36" y="130" fill="#94a3b8" font-size="9">Dispatch &amp; Validation</text>
  <text x="36" y="146" fill="#64748b" font-size="8">Boundary Gateway</text>

  <line x1="184" y1="112" x2="232" y2="112" stroke="{accent_color}" stroke-width="2" marker-end="url(#archArrow)" />

  <!-- Tier 2: Processing Core -->
  <rect x="238" y="56" width="170" height="112" rx="8" fill="#0f172a" stroke="{gate_color}" stroke-width="2" />
  <text x="250" y="82" fill="{gate_color}" font-size="11" font-weight="700">Tier 2: Processing Core</text>
  <text x="250" y="106" fill="#f8fafc" font-size="11" font-weight="600">{c2}</text>
  <text x="250" y="126" fill="#a78bfa" font-size="9">Transformation Pipeline</text>
  <text x="250" y="142" fill="#94a3b8" font-size="8">Low-Latency Execution</text>
  <text x="250" y="156" fill="#34d399" font-size="8">✓ Verified Policy</text>

  <line x1="408" y1="112" x2="452" y2="112" stroke="{core_color}" stroke-width="2" marker-end="url(#archGreen)" />

  <!-- Tier 3: Storage & State -->
  <rect x="458" y="64" width="160" height="96" rx="8" fill="#1e293b" stroke="{core_color}" stroke-width="1.5" />
  <text x="470" y="88" fill="{core_color}" font-size="11" font-weight="700">Tier 3: Persistence / State</text>
  <text x="470" y="112" fill="#f8fafc" font-size="11" font-weight="600">{c3}</text>
  <text x="470" y="130" fill="#94a3b8" font-size="9">Replicated Storage</text>
  <text x="470" y="146" fill="#64748b" font-size="8">ACID Consistency</text>
</svg>"""


class InterviewPrepService:
    def __init__(self, content_root: Optional[Path] = None):
        if content_root is None:
            content_root = Path(__file__).resolve().parent.parent / "content" / "interview_prep"
        self.content_root = content_root
        self._behavioral_cache: Optional[Dict[str, Any]] = None
        self._questions_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._explain_packs_cache: Dict[str, Dict[str, ExplainContextPack]] = {}

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

        pack = self._get_explain_pack(domain_id, found["slug"])

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
            explain_context=pack,
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

    def _get_explain_pack(self, domain_id: str, slug: str) -> ExplainContextPack:
        """Loads and returns the per-question ExplainContextPack from versioned storage."""
        if domain_id not in self._explain_packs_cache:
            packs_file = self.content_root / domain_id / "explain_packs.json"
            domain_packs = {}
            if packs_file.exists():
                try:
                    with open(packs_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        raw_packs = data.get("packs", {})
                        for s, p in raw_packs.items():
                            domain_packs[s] = ExplainContextPack(**p)
                    logger.info(f"Loaded {len(domain_packs)} explain context packs for {domain_id}")
                except Exception as e:
                    logger.warning(f"Failed to load explain_packs.json for {domain_id}: {e}")
            self._explain_packs_cache[domain_id] = domain_packs

        packs = self._explain_packs_cache.get(domain_id, {})
        if slug in packs:
            return packs[slug]

        # Case-insensitive / normalized match
        slug_clean = slug.lower().strip()
        for s, p in packs.items():
            if s.lower() == slug_clean:
                return p

        # On-the-fly synthesis if question was dynamically imported
        q = self.get_question_detail(domain_id, slug)
        return self._synthesize_fallback_pack(q) if q else ExplainContextPack(
            key_concepts=["System Architecture", "Performance", "Scalability"],
            common_misconceptions=["Ignoring latency trade-offs in distributed workloads"],
            analogy_seed="Like routing rush hour vehicles through coordinated express bypasses.",
            diagram_type="flow",
            diagram_brief="Client Dispatch -> Core Engine -> Analytics State",
            summary_seed="Establishes production mechanics, architectural constraints, and performance trade-offs.",
        )

    def _synthesize_fallback_pack(self, q: InterviewQuestionDetail) -> ExplainContextPack:
        """Synthesizes a dynamic ExplainContextPack directly from the question's content without generic security templates."""
        title = q.title or "Technical Architecture"
        content = q.markdown_content or ""
        cat = q.category or "Engineering"
        topic = q.topic or "Production Design"

        # Extract technical bold terms
        bold_terms = [b.strip() for b in re.findall(r'\*\*([A-Za-z0-9_\-\.\s]{3,30})\*\*', content) if len(b.strip()) > 2]
        concepts = bold_terms[:4] if bold_terms else [topic, cat, "Latency Profile"]
        while len(concepts) < 3:
            concepts.append(f"{cat} Concept {len(concepts)+1}")

        domain = (q.domain_id or "").lower()
        if "data" in domain:
            analogy = f"Like a distribution center sorting regional packages ({concepts[0]}) to keep highway delivery trucks on schedule."
            misconceptions = [
                f"Assuming {concepts[0]} executes eagerly rather than deferring work to the action phase.",
                f"Believing {concepts[0]} eliminates memory spill or partition skew."
            ]
        elif "ai" in domain:
            analogy = f"Like an encyclopedia index directing a researcher to precise pages ({concepts[0]}) to avoid rereading entire volumes."
            misconceptions = [
                f"Treating {concepts[0]} as zero-cost without accounting for quadratic attention overhead.",
                f"Assuming {concepts[0]} guarantees grounding without explicit delimiter constraints."
            ]
        else:
            analogy = f"Like an embassy checkpoint verifying biometric credentials ({concepts[0]}) before opening consular gates."
            misconceptions = [
                f"Relying solely on {concepts[0]} at the boundary while ignoring lateral authorization inside the network.",
                f"Assuming {concepts[0]} defaults provide complete coverage without auditing."
            ]

        # Determine diagram requirement
        tl = (title + " " + cat).lower()
        if any(p in tl for p in ["career", "role", "salary", "interview tips", "soft skills", "definition of"]):
            diag_type = "none"
            brief = None
        elif "difference" in tl or " vs " in tl or "compare" in tl:
            diag_type = "comparison"
            brief = f"Comparative trade-offs: {concepts[0]} vs {concepts[1] if len(concepts) > 1 else 'Alternative'}"
        else:
            diag_type = "flow"
            brief = f"{concepts[0]} Ingestion -> Processing Core -> State Storage"

        # Summary seed
        clean_text = content.replace("#", "").replace("*", "").strip()
        sentences = [s.strip() for s in clean_text.split(".") if len(s.strip()) > 25]
        summary = (sentences[0][:150] + ".") if sentences else f"{title} defines operational mechanics for {concepts[0]}."

        return ExplainContextPack(
            key_concepts=concepts[:5],
            common_misconceptions=misconceptions,
            analogy_seed=analogy,
            diagram_type=diag_type,
            diagram_brief=brief,
            summary_seed=summary,
        )

    def _build_structured_fallback_payload(
        self,
        q: InterviewQuestionDetail,
        lang: str = "en",
        reason: str = "AI service offline",
    ) -> StructuredAIExplanationPayload:
        """
        Builds a deterministic, schema-validated StructuredAIExplanationPayload.
        Uses the question's specific ExplainContextPack — completely eliminates generic/security template leftovers.
        """
        pack = self._get_explain_pack(q.domain_id, q.slug)
        concepts = pack.key_concepts or [q.topic or q.title]
        c1 = concepts[0]
        c2 = concepts[1] if len(concepts) > 1 else "Processing Core"
        c3 = concepts[2] if len(concepts) > 2 else "Storage Layer"

        domain = (q.domain_id or "").lower()
        if "data" in domain:
            actors = [
                Actor(id="client", role="client", label=f"{c1} Producer", description="Upstream client or event producer"),
                Actor(id="engine", role="system", label="Processing Engine", description=f"Distributed cluster executing {q.topic}"),
                Actor(id="storage", role="database", label="Analytics Storage", description="Target storage or table tier"),
            ]
            steps_naive = [
                ScenarioStep(order=1, from_actor="client", to_actor="engine", action="Dispatches unoptimized bulk query without partition tuning", payload="raw_query", annotation="Naive request", status="normal"),
                ScenarioStep(order=2, from_actor="engine", to_actor="storage", action="Triggers full cluster shuffle and memory spill to disk", payload="shuffled_partitions", annotation="Resource contention", status="normal"),
                ScenarioStep(order=3, from_actor="engine", to_actor="client", action="Returns response with degraded throughput and high latency", payload="slow_response", annotation="High latency", status="normal"),
            ]
            steps_prod = [
                ScenarioStep(order=1, from_actor="client", to_actor="engine", action="Dispatches tuned request with partition pruners and broadcast hints", payload="optimized_query", annotation="Structured request", status="normal"),
                ScenarioStep(order=2, from_actor="engine", to_actor="storage", action="Executes zero-copy vectorized scan and in-memory aggregation", payload="in_memory_partitions", annotation="Optimized execution", status="secure"),
                ScenarioStep(order=3, from_actor="engine", to_actor="client", action="Delivers low-latency query results within SLA", payload="subsecond_result", annotation="Production SLA met", status="secure"),
            ]
        elif "ai" in domain:
            actors = [
                Actor(id="user", role="client", label="Client Application", description="User interface dispatching prompts and queries"),
                Actor(id="pipeline", role="system", label="AI Pipeline / Model", description=f"Model execution engine processing {q.topic}"),
                Actor(id="store", role="database", label="Context & Vector Store", description="Index storing embeddings and retrieved documents"),
            ]
            steps_naive = [
                ScenarioStep(order=1, from_actor="user", to_actor="pipeline", action="Dispatches raw prompt without grounding or validation constraints", payload="raw_prompt", annotation="Ungrounded prompt", status="normal"),
                ScenarioStep(order=2, from_actor="pipeline", to_actor="store", action="Performs unindexed passage scan with quadratic context overhead", payload="context_scan", annotation="Context dilution", status="normal"),
                ScenarioStep(order=3, from_actor="pipeline", to_actor="user", action="Returns response with potential hallucination and high TTFT", payload="slow_completion", annotation="Degraded output", status="normal"),
            ]
            steps_prod = [
                ScenarioStep(order=1, from_actor="user", to_actor="pipeline", action="Dispatches structured request with delimiter tags and system guardrails", payload="grounded_prompt", annotation="Grounded request", status="normal"),
                ScenarioStep(order=2, from_actor="pipeline", to_actor="store", action="Executes hybrid sparse/dense retrieval with rank fusion", payload="top_k_chunks", annotation="Precise context", status="secure"),
                ScenarioStep(order=3, from_actor="pipeline", to_actor="user", action="Returns low-latency response verified against source facts", payload="verified_response", annotation="High accuracy", status="secure"),
            ]
        else: # Security
            actors = [
                Actor(id="alice", role="client", label="Alice (Requestor)", description="User or client requesting access"),
                Actor(id="auth_server", role="system", label="Enforcement Gateway", description=f"Security gate evaluating {q.topic}"),
                Actor(id="resource", role="database", label="Protected Resource", description="Underlying sensitive data or API service"),
            ]
            steps_naive = [
                ScenarioStep(order=1, from_actor="alice", to_actor="auth_server", action="Sends unverified request lacking signed proofs or token bindings", payload="unauthenticated_req", annotation="Unverified request", status="normal"),
                ScenarioStep(order=2, from_actor="auth_server", to_actor="resource", action="Permits direct execution without policy auditing or rate limiting", payload="unfiltered_pass", annotation="Missing guardrail", status="normal"),
                ScenarioStep(order=3, from_actor="resource", to_actor="alice", action="Returns unconstrained response exposing internal metadata", payload="unmasked_data", annotation="Policy gap", status="normal"),
            ]
            steps_prod = [
                ScenarioStep(order=1, from_actor="alice", to_actor="auth_server", action="Dispatches cryptographically signed request with PKCE/OAuth assertion", payload="signed_token", annotation="Validated token", status="normal"),
                ScenarioStep(order=2, from_actor="auth_server", to_actor="auth_server", action="Validates token claims, signature, and tenant RBAC policies", payload="claims_check", annotation="Policy verified", status="secure"),
                ScenarioStep(order=3, from_actor="auth_server", to_actor="alice", action="Returns scoped access token and deterministic protected payload", payload="scoped_access", annotation="Secure access granted", status="secure"),
            ]

        scenario = Scenario(
            title=f"Architectural Flow: {q.title[:60]}",
            variants=[
                ScenarioVariant(label="Without Recommended Setup (Naive / Unoptimized)", outcome="failure", steps=steps_naive),
                ScenarioVariant(label="With Production Architecture (Optimized / Hardened)", outcome="success", steps=steps_prod),
            ]
        )

        comparison_table = [
            ComparisonRow(criterion="Execution Latency", option_a="Naive: High resource contention and unindexed overhead", option_b="Production: Sub-second execution with deterministic caching"),
            ComparisonRow(criterion="Failure Boundary", option_a="Naive: Unbounded blast radius impacting adjacent workloads", option_b="Production: Isolated tenant boundaries with graceful degradation"),
            ComparisonRow(criterion="Maintenance / Scale", option_a="Naive: High incident rate under surge traffic", option_b="Production: Linear scalability with automated observability"),
        ]

        takeaways = [
            f"Master {c1} mechanics and explain production performance trade-offs.",
            f"Articulate how {c2} handles edge cases under unexpected traffic spikes.",
            f"Discuss real-world monitoring and observability metrics for {q.topic}.",
        ]

        mistakes = pack.common_misconceptions or [
            f"Assuming {c1} requires zero operational tuning in high-throughput environments.",
            f"Ignoring monitoring signals and metrics when scaling {c2} across nodes.",
        ]

        clean_fn = re.sub(r'[^a-z0-9]', '_', c1.lower()[:20]).strip('_') or 'runtime'
        code_sample = CodeSample(
            language="python",
            code=f"# Production implementation pattern for {q.topic}\ndef enforce_{clean_fn}_spec(config: dict) -> bool:\n    # Validate runtime invariants\n    validated = validate_parameters(config)\n    return initialize_runtime(validated)",
            explanation_lines=[
                CodeExplanationLine(line=3, note=f"Validates production parameters for {c1}"),
                CodeExplanationLine(line=4, note="Executes deterministic runtime verification"),
            ]
        )

        clean_svg = _generate_question_svg_diagram(q, pack)
        if clean_svg:
            from ..scraper.sanitizer import sanitize_svg
            clean_svg = sanitize_svg(clean_svg)

        return StructuredAIExplanationPayload(
            concept_summary=pack.summary_seed,
            analogy=pack.analogy_seed,
            actors=actors,
            scenario=scenario,
            code_sample=code_sample,
            comparison_table=comparison_table,
            takeaways=takeaways,
            common_mistakes=mistakes,
            has_diagram=bool(clean_svg),
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
                is_ai_generated=False,
            )

        lang = (language or "en").lower().strip()
        if lang not in ["en", "fr", "de"]:
            lang = "en"

        from .ai_gateway import get_active_provider, get_selected_model
        _active_prov = get_active_provider()
        _active_model = get_selected_model(_active_prov)
        model_key = f"{_active_prov.value}:{_active_model or 'default'}"
        SCHEMA_VERSION = 3

        # Load question-specific ExplainContextPack
        pack = self._get_explain_pack(domain_id, q.slug)

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
                                is_ai_generated="deterministic" not in (cached.model_name or ""),
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
        fallback_err: Optional[str] = None

        prompt = (
            "You are an expert technical interviewer and systems architect.\n"
            f"Explain the technical interview question below in {lang.upper()}.\n"
            "Return ONLY a valid JSON object matching the StructuredAIExplanationPayload schema.\n"
            "DO NOT output markdown code fences like ```json or conversational prose. Return raw valid JSON only.\n\n"
            f"Question Title: {q.title}\n"
            f"Domain / Category: {q.domain_title} / {q.category} ({q.topic})\n"
            f"Key Technical Concepts to Address: {', '.join(pack.key_concepts)}\n"
            f"Analogy Context Seed: {pack.analogy_seed}\n"
            f"Common Misconceptions to Address: {'; '.join(pack.common_misconceptions)}\n"
            f"Diagram Requirement: {'None (purely definitional concept; set has_diagram: false and svg_diagram: null)' if pack.diagram_type == 'none' else f'Type: {pack.diagram_type}. Node/flow brief: {pack.diagram_brief}'}\n"
            f"Source Technical Context: {q.markdown_content[:800]}\n\n"
            "Important Domain Guidelines:\n"
            "- Do NOT use cybersecurity vocabulary (such as attacker, exploit, adversary, attack blocked) unless this question is specifically about cybersecurity.\n"
            "- Ground your analogy in a concrete, relatable real-world human scenario fitting this exact topic (using tasteful emoji like 🏢, ⚙️, 🚀, 📦).\n"
            "- If a diagram is required, provide clean, valid standalone SVG markup with viewBox '0 0 640 200' using ONLY purely visual elements (<svg>, <rect>, <circle>, <path>, <line>, <text>, <g>, <defs>, <marker>). DO NOT include <script>, <foreignObject>, or external links.\n"
            "- Ensure scenario steps match declared actor IDs.\n"
            "Required JSON fields: concept_summary, analogy, actors (list of id, role, label, description), scenario (title, variants list each with label, outcome, steps list each with order, from, to, action, payload, annotation, status), code_sample (or null), comparison_table (list of criterion, option_a, option_b), takeaways (list of strings), common_mistakes (list of strings), has_diagram (bool), svg_diagram (string or null)."
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
                timeout_seconds=45.0,
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

                    # If model didn't output SVG but pack says concept needs one, provide dynamic visual
                    if not parsed_dict.get("svg_diagram") and pack.diagram_type != "none":
                        fallback_svg = _generate_question_svg_diagram(q, pack)
                        if fallback_svg:
                            clean_svg = sanitize_svg(fallback_svg)
                            parsed_dict["svg_diagram"] = clean_svg
                            parsed_dict["has_diagram"] = bool(clean_svg)

                    structured_payload = StructuredAIExplanationPayload(**parsed_dict)
                    model_used = model_key
                except Exception as parse_err:
                    logger.warning(f"Model JSON failed validation: {parse_err}")
                    fallback_err = f"Model output formatting issue: {parse_err}"
        except Exception as exc:
            logger.info(f"AI gateway generation unavailable ({exc}). Using deterministic structured fallback.")
            fallback_err = str(exc)

        # 3. Deterministic fallback layer if AI was offline or failed schema
        if not structured_payload:
            structured_payload = self._build_structured_fallback_payload(
                q, lang, reason=fallback_err or "AI offline"
            )
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
        is_ai = model_used != "deterministic-smart-ai"
        return QuestionAIExplainResponse(
            question_id=q.id,
            mode=mode,
            explanation=structured_payload.concept_summary,
            real_world_scenario=f"Case Scenario — {structured_payload.scenario.title} ({actor_names})",
            code_sample=structured_payload.code_sample.code if structured_payload.code_sample else None,
            key_interview_takeaways=structured_payload.takeaways,
            structured_payload=structured_payload,
            ai_model_used=model_used,
            is_ai_generated=is_ai,
            disclaimer=(
                f"Generated by {model_used}."
                if is_ai
                else f"Deep dive unavailable: {fallback_err or 'AI offline'}. Pre-written explanation remains active."
            ),
            fallback_reason=fallback_err if not is_ai else None,
            can_retry=not is_ai,
            has_diagram=structured_payload.has_diagram,
            svg_diagram=structured_payload.svg_diagram,
        )


    # ─── Two-Tier Explanation & Deep Dive Engine (v4) ─────────────────────────

    def load_raw_pre_explanation(self, domain_id: str, question_id_or_slug: str) -> Optional[dict]:
        """Loads authored pre-explanation overlay from disk if available."""
        track_map = {
            "data-engineering": "data_engineering",
            "data_engineering": "data_engineering",
            "security-engineering": "security_engineering",
            "security_engineering": "security_engineering",
            "ai-tech-interview": "ai_tech_interview",
            "ai_tech_interview": "ai_tech_interview",
        }
        track = track_map.get(domain_id, domain_id.replace("-", "_"))
        target = question_id_or_slug.strip()

        # Try by question_id first, then slug
        content_dir = Path(__file__).resolve().parent.parent / "content" / "interview_prep" / "pre_explanations" / track
        candidates = [
            content_dir / f"{target}.json",
            content_dir / f"{target.replace('_', '-')}.json",
        ]
        for candidate in candidates:
            if candidate.is_file():
                try:
                    return json.loads(candidate.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.warning(f"Failed to read pre-explanation file {candidate}: {e}")

        # Search directory if target was a slug
        if content_dir.is_dir():
            for f in content_dir.glob("*.json"):
                if f.name.startswith("PROGRESS"):
                    continue
                try:
                    obj = json.loads(f.read_text(encoding="utf-8"))
                    if obj.get("slug") == target or obj.get("question_id") == target:
                        return obj
                except Exception:
                    continue
        return None

    def get_question_pre_explanation(
        self, domain_id: str, question_slug: str, language: str = "en"
    ) -> QuestionExplanationResponse:
        """
        Instant Tier-1/Tier-2 Pre-Explanation fetch.
        Offline-ready. Returns authored explanation plus any cached AI deep dive.
        """
        q = self.get_question_detail(domain_id, question_slug)
        if not q:
            return QuestionExplanationResponse(
                has_pre_explanation=False,
                question_id=f"{domain_id}-{question_slug}",
                slug=question_slug,
                track=domain_id,
            )

        lang = (language or "en").lower().strip()
        from .ai_gateway import get_active_provider, get_selected_model
        _active_prov = get_active_provider()
        _active_model = get_selected_model(_active_prov)
        model_key = f"{_active_prov.value}:{_active_model or 'default'}"

        raw_pre = self.load_raw_pre_explanation(domain_id, q.id) or self.load_raw_pre_explanation(domain_id, q.slug)
        pre_data: Optional[PreExplanationData] = None
        if raw_pre:
            try:
                pre_data = PreExplanationData.model_validate(raw_pre)
            except Exception as pe_err:
                logger.warning(f"Pre-explanation validation error for {q.id}: {pe_err}")

        # Check DB cache for cached deep dive (schema_version = 4)
        cached_deep_dive: Optional[QuestionDeepDivePayload] = None
        try:
            with SessionLocal() as db:
                cached = db.query(InterviewExplanation).filter(
                    InterviewExplanation.question_id == q.id,
                    InterviewExplanation.language == lang,
                    InterviewExplanation.schema_version == 4,
                ).order_by(InterviewExplanation.id.desc()).first()
                if cached and cached.payload:
                    cached_deep_dive = QuestionDeepDivePayload.model_validate(cached.payload)
        except Exception as c_err:
            logger.debug(f"Deep dive cache lookup note: {c_err}")

        if pre_data:
            return QuestionExplanationResponse(
                has_pre_explanation=True,
                question_id=q.id,
                slug=q.slug,
                track=pre_data.track,
                category=pre_data.category or q.category,
                tier=pre_data.tier,
                version=pre_data.version,
                needs_diagram=pre_data.needs_diagram,
                needs_code=pre_data.needs_code,
                code_language=pre_data.code_language,
                code_snippet=pre_data.code_snippet,
                diagram_svg=pre_data.diagram_svg,
                diagram_caption=pre_data.diagram_caption,
                tldr=pre_data.content.tldr,
                simple_explanation=pre_data.content.simple_explanation,
                real_world_example=pre_data.content.real_world_example,
                why_it_matters_and_pitfalls=pre_data.content.why_it_matters_and_pitfalls,
                key_terms=pre_data.content.key_terms,
                cached_deep_dive=cached_deep_dive,
                ai_active_provider=_active_prov.value,
                ai_selected_model=_active_model,
            )

        # Fallback baseline when pre-authored explanation is not on disk yet
        summary_text = (q.markdown_content or q.raw_content or "").strip()
        paragraphs = [p.strip() for p in summary_text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        first_p = paragraphs[0] if paragraphs else q.title

        return QuestionExplanationResponse(
            has_pre_explanation=False,
            question_id=q.id,
            slug=q.slug,
            track=q.domain_id,
            category=q.category,
            tier=3,
            version=1,
            needs_diagram=False,
            needs_code=False,
            code_language=None,
            code_snippet=None,
            diagram_svg=None,
            diagram_caption=None,
            tldr=q.title,
            simple_explanation=first_p,
            real_world_example=None,
            why_it_matters_and_pitfalls=None,
            key_terms=q.tags or [],
            cached_deep_dive=cached_deep_dive,
            ai_active_provider=_active_prov.value,
            ai_selected_model=_active_model,
        )

    async def generate_question_deep_dive(
        self, domain_id: str, question_slug: str, language: str = "en", force_regenerate: bool = False
    ) -> QuestionDeepDiveResponse:
        """
        AI Deep Dive engine.
        Builds strictly upon the pre-written explanation without repeating it.
        Grounded in reference answer. Handles diagrams & code ONLY when flagged/genuinely needed.
        """
        q = self.get_question_detail(domain_id, question_slug)
        if not q:
            return QuestionDeepDiveResponse(
                success=False,
                question_id=f"{domain_id}-{question_slug}",
                slug=question_slug,
                error_reason="Question not found.",
                can_retry=False,
            )

        lang = (language or "en").lower().strip()
        from .ai_gateway import (
            get_active_provider,
            get_selected_model,
            generate_completion,
            OllamaProvider,
            GeminiProvider,
            AIProviderType,
            AIGatewayError,
            AIUnavailableError,
        )
        from ..scraper.sanitizer import sanitize_svg

        _active_prov = get_active_provider()
        _active_model = get_selected_model(_active_prov)
        model_key = f"{_active_prov.value}:{_active_model or 'default'}"
        DEEP_DIVE_SCHEMA_VERSION = 4

        # 1. Cache Check
        if not force_regenerate:
            try:
                with SessionLocal() as db:
                    cached = db.query(InterviewExplanation).filter(
                        InterviewExplanation.question_id == q.id,
                        InterviewExplanation.language == lang,
                        InterviewExplanation.model_name == model_key,
                        InterviewExplanation.schema_version == DEEP_DIVE_SCHEMA_VERSION,
                    ).first()
                    if cached and cached.payload:
                        payload = QuestionDeepDivePayload.model_validate(cached.payload)
                        return QuestionDeepDiveResponse(
                            success=True,
                            question_id=q.id,
                            slug=q.slug,
                            provider=_active_prov.value,
                            model=_active_model,
                            deep_dive=payload,
                        )
            except Exception as e:
                logger.debug(f"Deep dive cache read error: {e}")

        # 2. Provider Pre-flight Validation
        if _active_prov == AIProviderType.OLLAMA:
            health = OllamaProvider.check_health()
            if health.get("status") != "connected":
                return QuestionDeepDiveResponse(
                    success=False,
                    question_id=q.id,
                    slug=q.slug,
                    provider="ollama",
                    model=_active_model,
                    error_reason="Ollama is not running on 127.0.0.1:11434. Start Ollama and click Retry.",
                    can_retry=True,
                )
            installed = [m["name"] for m in health.get("models", [])]
            if _active_model and installed and _active_model not in installed:
                return QuestionDeepDiveResponse(
                    success=False,
                    question_id=q.id,
                    slug=q.slug,
                    provider="ollama",
                    model=_active_model,
                    error_reason=f"Model '{_active_model}' is not installed in Ollama. Available: {', '.join(installed)}.",
                    can_retry=True,
                )
        elif _active_prov == AIProviderType.GEMINI:
            from .ai_gateway import get_gemini_api_key
            if not get_gemini_api_key():
                return QuestionDeepDiveResponse(
                    success=False,
                    question_id=q.id,
                    slug=q.slug,
                    provider="gemini",
                    model=_active_model,
                    error_reason="Google Gemini API key not configured. Open AI Settings to enter your key.",
                    can_retry=False,
                )

        # 3. Grounding Context & Prompt
        raw_pre = self.load_raw_pre_explanation(domain_id, q.id) or self.load_raw_pre_explanation(domain_id, q.slug)
        pre_summary = ""
        needs_diagram_flag = False
        needs_code_flag = False
        if raw_pre:
            content_dict = raw_pre.get("content", {})
            tldr_val = content_dict.get('tldr', '')
            exp_val = content_dict.get('simple_explanation', '')
            scen_val = content_dict.get('real_world_example', '')
            pre_summary = f"TL;DR: {tldr_val} | Concept: {exp_val} | Scenario: {scen_val}"
            needs_diagram_flag = bool(raw_pre.get("needs_diagram"))
            needs_code_flag = bool(raw_pre.get("needs_code"))

        ref_answer = (q.markdown_content or q.raw_content or "")[:1800]
        lang_instruction = "English"
        if lang == "fr":
            lang_instruction = "Français"
        elif lang == "nl":
            lang_instruction = "Nederlands"
        elif lang == "de":
            lang_instruction = "Deutsch"

        prompt = (
            f"You are a principal staff engineer conducting an advanced technical interview.\n"
            f"Provide a technical deep dive in {lang_instruction} for the question below.\n\n"
            f"QUESTION: {q.title}\n"
            f"TRACK / CATEGORY: {q.domain_title} / {q.category} ({q.topic})\n\n"
            f"REPOSITORY REFERENCE ANSWER (GROUNDING TRUTH - DO NOT CONTRADICT):\n"
            f"{ref_answer}\n\n"
            f"PRE-EXPLANATION ALREADY READ BY CANDIDATE (DO NOT REPEAT):\n"
            f"{pre_summary if pre_summary else 'None available yet.'}\n\n"
            f"TASK INSTRUCTIONS:\n"
            f"1. Explain deeper mechanics, internals, trade-offs, and practical edge cases that go BEYOND the summary above.\n"
            f"2. Provide an extra real-world production incident or scenario.\n"
            f"3. List 2-4 critical engineering pitfalls.\n"
            f"4. List 2-4 tough interview follow-up questions.\n"
            f"5. CODE & DIAGRAM RULES:\n"
            f"   - Only output code if question genuinely requires query/implementation/config ({'Code is expected for this question' if needs_code_flag else 'Code is NOT expected unless strictly needed'}).\n"
            f"   - Only output diagram if architectural flow clarifies the concept ({'Diagram is expected' if needs_diagram_flag else 'Diagram is NOT expected'}). Standalone valid SVG viewBox '0 0 640 200'.\n\n"
            f"RETURN RAW JSON ONLY matching schema:\n"
            f'{{"deeper_explanation": "...", "extra_example": "...", "pitfalls": ["..."], "interview_followups": ["..."], "has_code": false, "code_language": null, "code_snippet": null, "has_diagram": false, "diagram_svg": null}}'
        )

        try:
            raw_resp = generate_completion(
                prompt=prompt,
                model=_active_model,
                provider=_active_prov,
                response_json=True,
                temperature=0.2,
                timeout_seconds=45.0,
            )
            clean_json = raw_resp.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.startswith("```"):
                clean_json = clean_json[3:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            parsed = json.loads(clean_json)

            # Sanitize diagram if model emitted one
            if parsed.get("diagram_svg"):
                clean_svg = sanitize_svg(parsed["diagram_svg"])
                parsed["diagram_svg"] = clean_svg
                parsed["has_diagram"] = bool(clean_svg)
            else:
                parsed["diagram_svg"] = None
                parsed["has_diagram"] = False

            # If diagram was not needed or generic, drop it
            if not needs_diagram_flag and not should_question_have_diagram(q):
                parsed["diagram_svg"] = None
                parsed["has_diagram"] = False

            # If code was not flagged and question is conceptual, drop code
            if not needs_code_flag and not any(k in q.title.lower() for k in ["query", "write", "code", "implement", "sql", "syntax"]):
                parsed["has_code"] = False
                parsed["code_snippet"] = None
                parsed["code_language"] = None

            deep_dive_payload = QuestionDeepDivePayload.model_validate(parsed)

            # Persist to database cache
            try:
                with SessionLocal() as db:
                    new_cache = InterviewExplanation(
                        question_id=q.id,
                        language=lang,
                        model_name=model_key,
                        payload=deep_dive_payload.model_dump(),
                        schema_version=DEEP_DIVE_SCHEMA_VERSION,
                        generated_at=datetime.utcnow(),
                    )
                    db.add(new_cache)
                    db.commit()
            except Exception as pe_err:
                logger.debug(f"Cache write note: {pe_err}")

            return QuestionDeepDiveResponse(
                success=True,
                question_id=q.id,
                slug=q.slug,
                provider=_active_prov.value,
                model=_active_model,
                deep_dive=deep_dive_payload,
            )

        except Exception as exc:
            err_msg = str(exc)
            if "rate limit" in err_msg.lower():
                clean_err = "Gemini rate limit reached. Please wait a few seconds before retrying."
            elif "timed out" in err_msg.lower():
                clean_err = "Generation timed out after 45s. Click Retry to try again."
            elif "not installed in ollama" in err_msg.lower():
                clean_err = err_msg
            else:
                clean_err = f"Provider unavailable ({err_msg})"

            logger.info(f"Deep dive generation failed: {clean_err}")
            return QuestionDeepDiveResponse(
                success=False,
                question_id=q.id,
                slug=q.slug,
                provider=_active_prov.value,
                model=_active_model,
                error_reason=clean_err,
                can_retry=True,
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
