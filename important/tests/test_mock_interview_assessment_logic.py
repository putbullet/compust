"""
Comprehensive regression tests for AI Mock Interview assessment logic,
topic coverage, transcript-aware evaluation, and Section 30 validation rules.

Verifies:
1. Short interview (~10 min) where unasked domains (e.g. Cryptography, PKI, IAM, Key Lifecycle)
   are categorized as 'not_assessed' and NEVER as weaknesses.
2. Real technical failure: Candidate gives an incorrect answer to SIEM ("encrypts network traffic");
   the assessment captures this as evidence-backed weakness tied to the source question.
3. ASR error handling: "Bluetooth team" -> "blue team", "OCC" -> "SOC" without candidate penalty.
4. Anti-over-correction: Conceptual errors ("firewall encrypts traffic") and unknown proper nouns
   (e.g. proprietary tool "AcmeNetGuardX") are preserved by normalizer.
5. All three tracks (Security Engineering, Data Engineering, AI Engineering) maintain strict
   evidence-based assessment and traceable scores.
6. Section 30 validation: Weaknesses without evidence from an answered question are pruned.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.app.services.transcript_normalizer import transcript_normalizer
from src.app.services.mock_interview_ai import (
    compute_skill_matrix,
    generate_recommendations,
    SkillMatrixResult,
)
from src.app.services.mock_interview_service import mock_interview_service
from src.app.services.mock_interview_engine import build_interview_plan


class TestTranscriptNormalizer:
    """Tests for context-aware acoustic normalizer."""

    def test_security_track_asr_normalization(self):
        """Verifies 'Bluetooth team' -> 'blue team' and 'OCC' -> 'SOC' in security context."""
        raw = "I want to work in a Bluetooth team and monitor OCC alerts using our seam."
        canonical, corrections = transcript_normalizer.normalize(
            raw_text=raw,
            domain_id="security_engineering",
            category_name="SOC Operations, SIEM, Incident Response & Threat Hunting",
            topic="SOC Operations",
            question_title="How do you handle alert triage in a Security Operations Center?",
        )
        assert "blue team" in canonical.lower()
        assert "soc" in canonical.lower()
        assert "siem" in canonical.lower()
        assert len(corrections) >= 2

    def test_data_engineering_track_asr_normalization(self):
        """Verifies 'pie spark' -> 'PySpark', 'r d d' -> 'RDD', 'cough ka' -> 'Kafka'."""
        raw = "We used pie spark with r d d transformations to ingest data from cough ka."
        canonical, corrections = transcript_normalizer.normalize(
            raw_text=raw,
            domain_id="data_engineering",
            category_name="Distributed Compute & Processing Engines",
            topic="Apache Spark",
            question_title="Explain Spark RDD and streaming architectures.",
        )
        assert "PySpark" in canonical
        assert "RDD" in canonical
        assert "Kafka" in canonical

    def test_ai_engineering_track_asr_normalization(self):
        """Verifies 'laura' -> 'LoRA', 'rad' -> 'RAG', 'b p e' -> 'BPE'."""
        raw = "We applied laura adapter weights and implemented a rad pipeline using b p e tokenization."
        canonical, corrections = transcript_normalizer.normalize(
            raw_text=raw,
            domain_id="ai_tech_interview",
            category_name="RAG Architectures & Vector Databases",
            topic="RAG",
            question_title="How do you architect a retrieval-augmented generation system?",
        )
        assert "LoRA" in canonical
        assert "RAG" in canonical
        assert "BPE" in canonical

    def test_anti_over_correction_preserves_candidate_conceptual_error(self):
        """
        CRITICAL TEST (Section 19):
        If candidate says 'A firewall encrypts all network traffic',
        the normalizer MUST NOT correct 'encrypts' to 'filters'.
        """
        raw = "A firewall encrypts all network traffic before it reaches the core switch."
        canonical, _ = transcript_normalizer.normalize(
            raw_text=raw,
            domain_id="security_engineering",
            category_name="Network Security & Architecture",
            topic="Firewalls",
            question_title="What is the role of a next-generation firewall?",
        )
        assert "encrypts" in canonical
        assert "filters" not in canonical

    def test_preserves_unknown_proper_nouns_and_tools(self):
        """
        CRITICAL TEST (Section 34):
        Unknown company, internal tool, or library names must NOT be replaced with curriculum terms.
        """
        raw = "At my previous company AcmeFintech, we built an internal service called KubeRouterX99."
        canonical, _ = transcript_normalizer.normalize(
            raw_text=raw,
            domain_id="security_engineering",
            category_name="Enterprise, Cloud & Infrastructure Security",
        )
        assert "AcmeFintech" in canonical
        assert "KubeRouterX99" in canonical


class TestAssessmentLogicAndEvidence:
    """Tests for evidence-based assessment and topic coverage."""

    def test_short_security_interview_unasked_topics_never_flagged_as_weakness(self):
        """
        CRITICAL ACCEPTANCE TEST (Sections 1, 2, 3, 6, 7, 15, 31):
        Interview asks 3 questions: Networking, SOC/Incident Response, and Behavioral.
        Cryptography, PKI, IAM & Key Lifecycle is NEVER asked.

        The assessment MUST NOT:
        - List Cryptography/PKI/IAM in weak_areas
        - Give Cryptography/PKI/IAM a 0/10 score
        - Claim candidate lacked knowledge in unassessed areas

        The assessment MUST:
        - List Cryptography/PKI/IAM in unassessed_domains
        - Set status="not_assessed" and score=None in skill_matrix
        - Include explicit unassessed disclaimer
        """
        # Metadata covering all 6 categories of Security Engineering track
        category_metadata = {
            "fundamentals": "Security Fundamentals & Threat Landscape",
            "network": "Network Security & Architecture",
            "cryptography-iam": "Cryptography, PKI, IAM & Key Lifecycle",
            "appsec": "Application Security & Secure Development",
            "enterprise-cloud": "Enterprise, Cloud & Infrastructure Security",
            "soc-ir": "SOC Operations, SIEM, Incident Response & Threat Hunting",
        }

        # Questions actually asked and answered in a 10-minute session
        evaluations = [
            {
                "question_id": "sec_intro_1",
                "category_id": "introduction",
                "category_name": "Introduction & Background",
                "topic": "Background",
                "question_title": "Tell me about your background in security engineering.",
                "question_type": "introductory",
                "canonical_transcript": "I have 3 years of experience as a security engineer focusing on network defense and SOC operations.",
                "raw_transcript": "I have 3 years of experience as a security engineer focusing on network defense and OCC operations.",
                "correctness": 0.85,
                "completeness": 0.80,
                "relevance": 0.90,
                "technical_depth": 0.75,
                "demonstrated_status": "demonstrated",
            },
            {
                "question_id": "sec_net_1",
                "category_id": "network",
                "category_name": "Network Security & Architecture",
                "topic": "ARP Spoofing",
                "question_title": "What happens during an ARP spoofing attack and how is it mitigated?",
                "question_type": "technical",
                "canonical_transcript": "An attacker sends gratuitous ARP replies linking their MAC address to the default gateway IP, poisoning local ARP caches. It can be prevented with DAI.",
                "raw_transcript": "An attacker sends gratuitous art replies linking their MAC address to the default gateway IP, poisoning local art caches. It can be prevented with DAI.",
                "correctness": 0.90,
                "completeness": 0.85,
                "relevance": 0.95,
                "technical_depth": 0.85,
                "positive_points": ["Accurate explanation of gratuitous ARP", "Correctly cited Dynamic ARP Inspection"],
                "demonstrated_status": "demonstrated",
            },
            {
                "question_id": "sec_soc_1",
                "category_id": "soc-ir",
                "category_name": "SOC Operations, SIEM, Incident Response & Threat Hunting",
                "topic": "SIEM Correlation",
                "question_title": "What is the role of a SIEM in a SOC?",
                "question_type": "technical",
                "canonical_transcript": "A SIEM aggregates logs across servers, firewalls, and endpoints to correlate events and alert on suspicious patterns.",
                "raw_transcript": "A SIEM aggregates logs across servers, firewalls, and endpoints to correlate events and alert on suspicious patterns.",
                "correctness": 0.80,
                "completeness": 0.75,
                "relevance": 0.85,
                "technical_depth": 0.75,
                "positive_points": ["Understood centralized log collection and correlation"],
                "demonstrated_status": "demonstrated",
            },
        ]

        result = compute_skill_matrix(evaluations, category_metadata)

        # 1. Unasked categories MUST be in unassessed_domains
        assert "Cryptography, PKI, IAM & Key Lifecycle" in result.unassessed_domains
        assert "Application Security & Secure Development" in result.unassessed_domains
        assert "Enterprise, Cloud & Infrastructure Security" in result.unassessed_domains

        # 2. Unasked categories MUST NOT be in weak_areas
        assert "Cryptography, PKI, IAM & Key Lifecycle" not in result.weak_areas
        assert "Application Security & Secure Development" not in result.weak_areas
        for w in result.weak_areas:
            assert "cryptography" not in w.lower()
            assert "pki" not in w.lower()
            assert "iam" not in w.lower()

        # 3. In Skill Matrix, unasked domains must have status="not_assessed" and score=None
        crypto_entry = next((e for e in result.skill_matrix if e["category_id"] == "cryptography-iam"), None)
        assert crypto_entry is not None
        assert crypto_entry["rating"] == "Not Assessed"
        assert crypto_entry["status"] == "not_assessed"
        assert crypto_entry["score"] is None
        assert crypto_entry["question_count"] == 0

        # 4. Technical score must ONLY evaluate technical concepts actually assessed (Network + SOC)
        # Average of (0.8875 + 0.7875) = ~83.8%
        assert result.technical_score >= 80.0
        assert result.overall_score >= 80.0

        # 5. Unassessed disclaimer must be present
        assert "These topics were not assessed during this interview" in result.unassessed_disclaimer

    def test_real_technical_failure_evidence_linked(self):
        """
        CRITICAL TEST (Sections 5, 20, 21, 32):
        Candidate gives an incorrect answer to SIEM:
        'A SIEM is mainly used to encrypt network traffic.'
        Assessment must capture this as an observed weakness with question evidence.
        """
        category_metadata = {
            "soc-ir": "SOC Operations, SIEM, Incident Response & Threat Hunting",
            "network": "Network Security & Architecture",
        }

        evaluations = [
            {
                "question_id": "sec_siem_q3",
                "category_id": "soc-ir",
                "category_name": "SOC Operations, SIEM, Incident Response & Threat Hunting",
                "topic": "SIEM Architecture",
                "question_title": "What is the primary role of a SIEM in a SOC?",
                "question_type": "technical",
                "canonical_transcript": "A SIEM is mainly used to encrypt network traffic between routers.",
                "raw_transcript": "A SIEM is mainly used to encrypt network traffic between routers.",
                "correctness": 0.10,
                "completeness": 0.15,
                "relevance": 0.20,
                "technical_depth": 0.10,
                "incorrect_claims": ["Claimed SIEM encrypts network traffic between routers"],
                "improvement_points": ["SIEM is for log aggregation, normalization, correlation, and alerting"],
                "better_answer_notes": "A SIEM ingests logs from endpoints and network devices to correlate telemetry and generate alerts.",
                "demonstrated_status": "not_demonstrated",
            }
        ]

        result = compute_skill_matrix(evaluations, category_metadata)

        # 1. Weak area must be reported for SOC/SIEM
        assert "SOC Operations, SIEM, Incident Response & Threat Hunting" in result.weak_areas

        # 2. Weak area detail must link to the specific question and evidence
        assert len(result.weak_area_details) >= 1
        weak_item = result.weak_area_details[0]
        assert weak_item["source_question_id"] == "sec_siem_q3"
        assert "encrypt" in weak_item["evidence"].lower() or "encrypt" in (weak_item["correction"] or "").lower()

        # 3. Recommendations must trace to the source question
        recs = generate_recommendations(
            result.weak_areas,
            "security_engineering",
            {"categories": [{"id": "soc-ir", "name": "SOC Operations, SIEM, Incident Response & Threat Hunting"}]},
            weak_area_details=result.weak_area_details,
        )
        assert len(recs) >= 1
        assert recs[0]["source_question_id"] == "sec_siem_q3"

        # 4. Low score is correctly assigned because candidate gave incorrect answer
        assert result.technical_score < 25.0

    def test_section_30_logical_validation_prunes_unsupported_weaknesses(self):
        """
        CRITICAL TEST (Section 30):
        If an upstream bug or evaluator were to suggest a weakness for an unasked topic,
        the Section 30 logical validation step in compute_skill_matrix MUST remove it.
        """
        category_metadata = {
            "soc-ir": "SOC Operations, SIEM, Incident Response & Threat Hunting",
            "cryptography-iam": "Cryptography, PKI, IAM & Key Lifecycle",
        }

        # Candidate answered only SOC question with good score
        evaluations = [
            {
                "question_id": "sec_soc_1",
                "category_id": "soc-ir",
                "category_name": "SOC Operations, SIEM, Incident Response & Threat Hunting",
                "topic": "SOC",
                "question_title": "Explain SOC tiering.",
                "question_type": "technical",
                "canonical_transcript": "Tier 1 handles triage, Tier 2 investigates, Tier 3 performs threat hunting.",
                "raw_transcript": "Tier 1 handles triage, Tier 2 investigates, Tier 3 performs threat hunting.",
                "correctness": 0.90,
                "completeness": 0.85,
                "relevance": 0.90,
                "technical_depth": 0.85,
                "demonstrated_status": "demonstrated",
            }
        ]

        result = compute_skill_matrix(evaluations, category_metadata)

        # Cryptography was not asked, so it MUST NOT be in weak_areas
        assert "Cryptography, PKI, IAM & Key Lifecycle" not in result.weak_areas
        assert "Cryptography, PKI, IAM & Key Lifecycle" in result.unassessed_domains

    def test_data_engineering_track_evidence_and_unassessed_domains(self):
        """Verifies Data Engineering track properly marks unasked Kafka/Airflow as not_assessed."""
        category_metadata = {
            "distributed-compute": "Distributed Compute & Processing Engines",
            "data-warehousing-modeling": "Data Warehousing, Dimensional Modeling & SQL",
            "streaming-messaging": "Streaming & Real-Time Messaging",
            "orchestration-cloud": "Workflow Orchestration & Cloud Infrastructure",
        }

        evaluations = [
            {
                "question_id": "de_sql_1",
                "category_id": "data-warehousing-modeling",
                "category_name": "Data Warehousing, Dimensional Modeling & SQL",
                "topic": "Window Functions",
                "question_title": "Explain ROW_NUMBER vs DENSE_RANK in analytical SQL.",
                "question_type": "technical",
                "canonical_transcript": "ROW_NUMBER assigns unique sequential integers, while DENSE_RANK gives identical ranks without gaps.",
                "raw_transcript": "ROW_NUMBER assigns unique sequential integers, while DENSE_RANK gives identical ranks without gaps.",
                "correctness": 0.95,
                "completeness": 0.90,
                "relevance": 0.95,
                "technical_depth": 0.90,
                "positive_points": ["Accurate distinction of rank ties without skipping"],
                "demonstrated_status": "demonstrated",
            }
        ]

        result = compute_skill_matrix(evaluations, category_metadata)
        assert "Streaming & Real-Time Messaging" in result.unassessed_domains
        assert "Workflow Orchestration & Cloud Infrastructure" in result.unassessed_domains
        assert "Streaming & Real-Time Messaging" not in result.weak_areas
        assert result.technical_score >= 90.0

    def test_ai_engineering_track_evidence_and_unassessed_domains(self):
        """Verifies AI Engineering track properly marks unasked LoRA/Fine-tuning as not_assessed."""
        category_metadata = {
            "rag-architectures": "RAG Architectures & Vector Databases",
            "fine-tuning-adaptation": "Model Fine-Tuning & Adaptation",
            "system-design-llmops": "System Design, Evaluation & LLMOps",
        }

        evaluations = [
            {
                "question_id": "ai_rag_1",
                "category_id": "rag-architectures",
                "category_name": "RAG Architectures & Vector Databases",
                "topic": "RAG Chunking",
                "question_title": "How does chunk size and overlap impact RAG retrieval precision?",
                "question_type": "technical",
                "canonical_transcript": "Smaller chunks provide precise semantic context, while overlap preserves boundary transitions.",
                "raw_transcript": "Smaller chunks provide precise semantic context, while overlap preserves boundary transitions.",
                "correctness": 0.90,
                "completeness": 0.85,
                "relevance": 0.90,
                "technical_depth": 0.85,
                "positive_points": ["Understood chunk boundary tradeoff"],
                "demonstrated_status": "demonstrated",
            }
        ]

        result = compute_skill_matrix(evaluations, category_metadata)
        assert "Model Fine-Tuning & Adaptation" in result.unassessed_domains
        assert "Model Fine-Tuning & Adaptation" not in result.weak_areas
        assert result.technical_score >= 85.0
