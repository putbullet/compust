"""
Interview Prep Content & Query Service.
Provides fast in-memory access to structured domains, categories, topics, questions,
multilingual behavioral preparation, and optional local AI explanation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..schemas_interview_prep import (
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

logger = logging.getLogger("compust.interview_prep.service")

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
        "hero_illustration": "/illustrations/ai_engineering_banner.png",
        "source_repository": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
        "source_license": "Public Open Source (Outcome School / Amit Shekhar)",
        "source_url": "https://github.com/amitshekhariitbhu/ai-engineering-interview-questions",
    },
]


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

    async def explain_with_ai(
        self,
        domain_id: str,
        question_slug: str,
        mode: str = "simplify",
        user_draft_answer: Optional[str] = None,
    ) -> QuestionAIExplainResponse:
        """
        Uses the local Ollama LLM to generate an educational breakdown or evaluate a user draft answer.
        Output is enriched with real-world scenarios, code snippets, and interview takeaways.
        """
        q = self.get_question_detail(domain_id, question_slug)
        if not q:
            return QuestionAIExplainResponse(
                question_id=f"{domain_id}-{question_slug}",
                mode=mode,
                explanation="Question not found.",
                ai_model_used="none",
            )

        smart_data = self._build_smart_explanation_fields(q)

        settings = get_settings()
        ollama_url = settings.ollama_url or "http://127.0.0.1:11434"
        model = settings.default_ai_model or "qwen2.5:0.5b"

        prompt = ""
        if mode == "simplify":
            prompt = (
                f"You are a Senior Principal Technical Interviewer. Explain the following technical interview question "
                f"in simple, intuitive, real-world terms for an engineer preparing for a technical interview.\n\n"
                f"Question: {q.title}\n"
                f"Category: {q.category} ({q.topic})\n"
                f"Core Content Summary: {q.markdown_content[:1500]}\n\n"
                f"Structure your response:\n"
                f"1. Real-World Case Scenario (A concrete narrative with named actors e.g. Alice the engineer and Bob the adversary or colleague illustrating what happens step-by-step in practice)\n"
                f"2. Core Technical Mechanics\n"
                f"3. Practical Sample Code / Command Blueprint (if technical)\n"
                f"4. 3 Crucial Points to Pass the Interview."
            )
        elif mode == "mock_feedback" and user_draft_answer:
            prompt = (
                f"You are an empathetic yet rigorous Technical Interviewer. Evaluate this candidate's draft answer.\n\n"
                f"Question: {q.title}\n"
                f"Candidate's Draft Answer:\n{user_draft_answer}\n\n"
                f"Reference Concepts:\n{q.markdown_content[:1500]}\n\n"
                f"Provide constructive, structured feedback:\n"
                f"1. Strengths of the candidate's answer\n"
                f"2. Missing technical depth or nuances\n"
                f"3. Concrete suggested revision for maximum impact."
            )
        else:
            prompt = (
                f"Provide a realistic follow-up interview question and answer evaluation for:\n"
                f"Question: {q.title}\n"
                f"Context: {q.markdown_content[:1200]}"
            )

        explanation = ""
        model_used = "deterministic-smart-ai"

        try:
            import httpx
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2, "top_p": 0.9}
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    explanation = data.get("response", "").strip()
                    model_used = model
        except Exception as e:
            logger.warning(f"Ollama local explanation unavailable ({e}), using structured smart heuristic.")

        if not explanation:
            # Deterministic fallback breakdown when local AI is offline
            explanation = (
                f"### High-Yield Concept Breakdown\n\n"
                f"**Real-World Scenario**: {smart_data['real_world_scenario']}\n\n"
                f"**3 Core Takeaways to Articulate**:\n" +
                "\n".join([f"{i+1}. {pt}" for i, pt in enumerate(smart_data["key_interview_takeaways"])])
            )
            if smart_data["code_sample"]:
                explanation += f"\n\n**Production Code / Pattern Sample**:\n```python\n{smart_data['code_sample']}\n```"

        return QuestionAIExplainResponse(
            question_id=q.id,
            mode=mode,
            explanation=explanation,
            real_world_scenario=smart_data["real_world_scenario"],
            code_sample=smart_data["code_sample"],
            key_interview_takeaways=smart_data["key_interview_takeaways"],
            ai_model_used=model_used,
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
