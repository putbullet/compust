"""
Context-Aware Transcript Normalizer for AI Mock Interview.

Transforms raw ASR transcripts into canonical transcripts by resolving
domain-specific speech recognition acoustic ambiguities while strictly
respecting two non-negotiable boundaries:

1. ANTI-OVER-CORRECTION:
   Never "correct" a real candidate conceptual error into a correct technical statement.
   For example, "A firewall encrypts all network traffic" must remain "encrypts",
   NOT converted to "filters".

2. UNKNOWN TERM PRESERVATION:
   Never replace unknown company names, proprietary internal tools, or novel project
   names with common curriculum terms.

Supported Tracks:
- Security Engineering: "OCC" -> "SOC", "Bluetooth team" -> "blue team", "sim/seam" -> "SIEM", "art spoofing" -> "ARP spoofing", etc.
- Data Engineering: "pie spark" -> "PySpark", "r d d" -> "RDD", "cough ka" -> "Kafka", "tag" -> "DAG", etc.
- AI Engineering: "laura/lore a" -> "LoRA", "rad" -> "RAG", "b p e" -> "BPE", "m c p" -> "MCP", etc.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Rule structure: (pattern, replacement, required_context_keywords_or_empty)
# Case-insensitive word-boundary replacements.
_SECURITY_CORRECTIONS: List[Tuple[str, str, List[str]]] = [
    (r"\bBluetooth team\b", "blue team", []),
    (r"\bbluetooth team\b", "blue team", []),
    (r"\bBluetooth teams\b", "blue teams", []),
    (r"\bread team\b", "red team", ["security", "offensive", "pentest", "adversary", "simulation"]),
    (r"\bOCC\b", "SOC", []),
    (r"\bocc\b", "SOC", ["alert", "investigat", "monitor", "analyst", "tier", "siem", "incident", "triage"]),
    (r"\bseam\b", "SIEM", ["log", "alert", "monitor", "soc", "correlat", "incident", "splunk"]),
    (r"\bsim\b", "SIEM", ["log", "alert", "monitor", "soc", "correlat", "incident", "security information"]),
    (r"\bart spoofing\b", "ARP spoofing", []),
    (r"\bheart spoofing\b", "ARP spoofing", ["network", "packet", "cache", "mac", "poisoning"]),
    (r"\bp\s*k\s*i\b", "PKI", []),
    (r"\bi\s*a\s*m\b", "IAM", []),
    (r"\bx\s*s\s*s\b", "XSS", []),
    (r"\bc\s*s\s*r\s*f\b", "CSRF", []),
    (r"\bd\s*dos\b", "DDoS", []),
    (r"\bdee dos\b", "DDoS", []),
    (r"\bc\s*and\s*c\b", "C2", ["server", "botnet", "command", "control", "malware"]),
    (r"\bcommand and control\b", "C2 (Command and Control)", ["server", "botnet", "traffic"]),
]

_DATA_CORRECTIONS: List[Tuple[str, str, List[str]]] = [
    (r"\bpie\s*spark\b", "PySpark", []),
    (r"\bpi\s*spark\b", "PySpark", []),
    (r"\br\s*d\s*d\b", "RDD", []),
    (r"\bare\s*d\s*d\b", "RDD", []),
    (r"\bcough\s*ka\b", "Kafka", []),
    (r"\bcaf\s*ca\b", "Kafka", []),
    (r"\bkaf\s*ca\b", "Kafka", []),
    (r"\btag\b", "DAG", ["spark", "airflow", "directed", "acyclic", "graph", "schedule", "execution"]),
    (r"\bd\s*a\s*g\b", "DAG", []),
    (r"\bs\s*c\s*d\b", "SCD", ["type", "dimension", "history"]),
    (r"\bc\s*d\s*c\b", "CDC", ["change", "data", "capture", "debezium", "streaming"]),
    (r"\bpar\s*k\b", "Parquet", ["file", "columnar", "storage", "snappy", "format"]),
    (r"\bparkette\b", "Parquet", []),
]

_AI_CORRECTIONS: List[Tuple[str, str, List[str]]] = [
    (r"\blaura\b", "LoRA", ["fine-tuning", "finetuning", "adapter", "weights", "peft", "rank", "matrix", "model"]),
    (r"\blore\s*a\b", "LoRA", ["fine-tuning", "finetuning", "adapter", "weights", "peft", "rank", "matrix", "model"]),
    (r"\brad\b", "RAG", ["retrieval", "augmented", "generation", "vector", "embedding", "chunk", "llm"]),
    (r"\br\s*a\s*g\b", "RAG", []),
    (r"\bb\s*p\s*e\b", "BPE", []),
    (r"\bbee\s*pee\s*ee\b", "BPE", []),
    (r"\bm\s*c\s*p\b", "MCP", ["model", "context", "protocol", "agent", "tool"]),
    (r"\br\s*l\s*h\s*f\b", "RLHF", []),
    (r"\bd\s*p\s*o\b", "DPO", []),
    (r"\bl\s*l\s*m\b", "LLM", []),
    (r"\bl\s*l\s*ms\b", "LLMs", []),
    (r"\bk\s*v\s*cache\b", "KV cache", []),
    (r"\bk\s*v\s*caching\b", "KV caching", []),
]


class TranscriptNormalizer:
    """Normalizes raw transcripts to canonical transcripts with context awareness."""

    def normalize(
        self,
        raw_text: str,
        domain_id: Optional[str] = None,
        category_name: Optional[str] = None,
        topic: Optional[str] = None,
        question_title: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Normalize transcript text into a canonical representation.
        Returns: (canonical_text, list_of_applied_corrections)
        """
        if not raw_text or not raw_text.strip():
            return raw_text, []

        context_blob = " ".join([
            (domain_id or "").lower(),
            (category_name or "").lower(),
            (topic or "").lower(),
            (question_title or "").lower(),
            raw_text.lower(),
        ])

        # Select domain rules
        rules: List[Tuple[str, str, List[str]]] = []
        domain_clean = (domain_id or "").lower()

        if "security" in domain_clean or "sec_" in (question_title or "").lower():
            rules.extend(_SECURITY_CORRECTIONS)
        elif "data" in domain_clean or "de_" in (question_title or "").lower():
            rules.extend(_DATA_CORRECTIONS)
        elif "ai" in domain_clean or "ml" in domain_clean:
            rules.extend(_AI_CORRECTIONS)
        else:
            # Check context keywords if domain_id was generic
            if any(k in context_blob for k in ["soc", "siem", "firewall", "pki", "iam", "cyber", "malware", "arp"]):
                rules.extend(_SECURITY_CORRECTIONS)
            if any(k in context_blob for k in ["spark", "kafka", "parquet", "airflow", "warehouse", "dag", "rdd"]):
                rules.extend(_DATA_CORRECTIONS)
            if any(k in context_blob for k in ["transformer", "llm", "lora", "rag", "embedding", "vector", "tokeniz"]):
                rules.extend(_AI_CORRECTIONS)

        normalized = raw_text
        corrections: List[Dict[str, str]] = []

        for pattern, replacement, required_keywords in rules:
            # If required keywords specified, ensure at least one is present in context
            if required_keywords and not any(kw in context_blob for kw in required_keywords):
                continue

            matches = list(re.finditer(pattern, normalized, flags=re.IGNORECASE))
            if matches:
                # Apply replacement
                new_text, count = re.subn(pattern, replacement, normalized, flags=re.IGNORECASE)
                if count > 0:
                    for m in matches:
                        matched_str = m.group(0)
                        if matched_str != replacement:
                            corrections.append({
                                "original": matched_str,
                                "replacement": replacement,
                                "rule": pattern,
                            })
                    normalized = new_text

        return normalized, corrections


# Global singleton instance
transcript_normalizer = TranscriptNormalizer()
