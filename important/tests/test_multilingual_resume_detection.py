import pytest
from src.app.services.resume_parser import (
    structure_resume_text,
    parse_skills_list,
    parse_languages_list,
    MULTILINGUAL_SECTION_HEADERS,
)
from src.app.repositories.resume import (
    build_parsed_sections_from_structured_data,
    build_raw_text_from_structured_data,
)
from src.app.services.resume_customization import analyze_resume_alignment
from src.app.models import Job, Resume


# --- 1. Multilingual Raw Text Fixtures ---

ENGLISH_RESUME_TEXT = """
John Doe
Software Engineer
john@example.com | +1 555-0199 | New York, NY

Summary
Passionate full-stack developer with 5+ years of experience building scalable distributed web applications.

Experience
Senior Developer at Acme Corp (2021 - Present)
- Led development of real-time trading dashboard using Python and React.
- Reduced API latency by 40% using Redis caching and asynchronous workers.

Education
B.S. in Computer Science at MIT (2017 - 2021)

Skills
Python, FastAPI, React, TypeScript, Docker, PostgreSQL, Redis, Git

Languages
English (Native), French (Fluent), German (Basic)

Projects
Cloud Monitor: High throughput telemetry ingestion platform built with Go and Kafka.
"""

FRENCH_RESUME_TEXT = """
Soulaimane Ettabaa
Ingénieur Sécurité & Systèmes
soulaimane@example.com | +33 6 12 34 56 78 | Paris, France

Profil
Élève ingénieur en 2ème année en Sécurité des Technologies de l'Information. Passionné par la cybersécurité offensive et le devsecops.

Expériences professionnelles
Stagiaire Analyste SOC at CyberSec SAS (2023 - 2024)
- Détection et réponse aux incidents de sécurité avec Wazuh et YARA.
- Automatisation des workflows d'investigation en Python et Bash.

Formation
Diplôme d'Ingénieur en Cybersécurité at ENSIMAG (2022 - 2025)

Compétences
Sécurité des systèmes, Analyse des vulnérabilités, Python, C, SQL, Linux, Bash, Git, YARA, OWASP

Langues
Français (natif), Anglais (courant), Arabe (langue maternelle)

Projets
Audit Scanner: Outil d'analyse statique de vulnérabilités pour applications Django.
"""

GERMAN_RESUME_TEXT = """
Hans Schmidt
Senior Softwareentwickler
hans.schmidt@example.de | +49 89 123456 | München, Deutschland

Zusammenfassung
Erfahrener Softwareentwickler mit fundierten Kenntnissen in der Entwicklung hochverfügbarer Cloud-Architekturen.

Berufserfahrung
Lead Entwickler at Tech GmbH (2020 - Heute)
- Konzeption und Implementierung von Microservices in Python und Go.
- Optimierung von CI/CD-Pipelines mit Kubernetes und Docker.

Ausbildung
Master of Science in Informatik at TU München (2015 - 2020)

Kenntnisse
Python, Go, Kubernetes, Docker, PostgreSQL, Linux, Git, Microservices

Sprachen
Deutsch (Muttersprache), Englisch (Verhandlungssicher), Französisch (Grundkenntnisse)

Projekte
KubeDeploy: Automatisierungstool für Multi-Cluster-Deployments.
"""


def test_multilingual_headers_dictionary_completeness():
    """Verify that multilingual dictionary contains required languages and canonical sections."""
    required_sections = ["summary", "experience", "education", "skills", "projects", "certifications", "languages"]
    required_languages = ["en", "fr", "de"]

    for sec in required_sections:
        assert sec in MULTILINGUAL_SECTION_HEADERS, f"Missing canonical section: {sec}"
        for lang in required_languages:
            assert lang in MULTILINGUAL_SECTION_HEADERS[sec], f"Missing {lang} for section {sec}"
            assert len(MULTILINGUAL_SECTION_HEADERS[sec][lang]) > 0


def test_english_resume_parsing():
    parsed = structure_resume_text(ENGLISH_RESUME_TEXT)
    assert len(parsed["skills"]) >= 6
    assert "python" in [s.lower() for s in parsed["skills"]]
    assert "fastapi" in [s.lower() for s in parsed["skills"]]
    assert len(parsed["languages"]) == 3
    assert any("english" in l.lower() for l in parsed["languages"])
    assert any("french" in l.lower() for l in parsed["languages"])
    assert bool(parsed["summary"])
    assert bool(parsed["experience"])
    assert bool(parsed["education"])


def test_french_resume_parsing():
    parsed = structure_resume_text(FRENCH_RESUME_TEXT)
    assert len(parsed["skills"]) >= 6
    assert any("python" in s.lower() for s in parsed["skills"])
    assert any("linux" in s.lower() for s in parsed["skills"])
    assert len(parsed["languages"]) == 3
    assert any("français" in l.lower() or "francais" in l.lower() for l in parsed["languages"])
    assert any("anglais" in l.lower() for l in parsed["languages"])
    assert bool(parsed["summary"])
    assert bool(parsed["experience"])
    assert bool(parsed["education"])


def test_german_resume_parsing():
    parsed = structure_resume_text(GERMAN_RESUME_TEXT)
    assert len(parsed["skills"]) >= 6
    assert any("python" in s.lower() for s in parsed["skills"])
    assert any("kubernetes" in s.lower() for s in parsed["skills"])
    assert len(parsed["languages"]) == 3
    assert any("deutsch" in l.lower() for l in parsed["languages"])
    assert any("englisch" in l.lower() for l in parsed["languages"])
    assert bool(parsed["summary"])
    assert bool(parsed["experience"])
    assert bool(parsed["education"])


def test_structured_data_sync_and_match_alignment():
    """Verify that a French structured resume syncs parsed_sections and delivers non-zero skill matches."""
    sample_french_structured = {
        "profile": {
            "full_name": "Soulaimane Ettabaa",
            "summary": "Élève ingénieur en Sécurité des SI.",
            "email": "soulaimane@example.com",
            "phone": "+33 6 00 00 00 00",
            "location": "Paris",
        },
        "skills": [
            {"id": "s1", "name": "Python", "category": "Core"},
            {"id": "s2", "name": "Linux", "category": "Core"},
            {"id": "s3", "name": "SQL", "category": "Core"},
            {"id": "s4", "name": "Git", "category": "Core"},
            {"id": "s5", "name": "YARA", "category": "Core"},
        ],
        "languages": [
            {"id": "l1", "language": "Français", "proficiency": "fluent"},
            {"id": "l2", "language": "Anglais", "proficiency": "fluent"},
            {"id": "l3", "language": "Arabe", "proficiency": "native"},
        ],
        "experience": [
            {
                "company": "CyberSec",
                "title": "Analyste SOC",
                "start_date": "2023",
                "end_date": "2024",
                "description": "Utilisation de Python et Linux pour analyser des attaques.",
            }
        ],
        "education": [
            {"institution": "ENSIMAG", "degree": "Diplôme d'Ingénieur", "field_of_study": "Cyber"}
        ],
        "projects": [],
        "certifications": [],
    }

    # 1. Test derivation of parsed_sections and raw_text
    parsed = build_parsed_sections_from_structured_data(sample_french_structured)
    raw_text = build_raw_text_from_structured_data(sample_french_structured)

    assert len(parsed["skills"]) == 5
    assert "Python" in parsed["skills"]
    assert "Linux" in parsed["skills"]
    assert len(parsed["languages"]) == 3
    assert any("Français" in l for l in parsed["languages"])
    assert "Python" in raw_text
    assert "Analyste SOC" in raw_text

    # 2. Test match alignment
    job = Job(
        title="Python Cybersecurity Developer",
        description="Looking for an engineer proficient with Python, Linux, and SQL.",
    )
    resume = Resume(
        user_id=1,
        title="Master Resume",
        filename="master_professional_resume.json",
        structured_data=sample_french_structured,
        parsed_sections=parsed,
        raw_text=raw_text,
    )

    alignment = analyze_resume_alignment(
        job=job,
        job_skills=["Python", "Linux", "SQL", "Docker"],
        resume=resume,
    )

    # Demonstrated skills must NOT be empty!
    assert len(alignment["already_demonstrated"]) >= 2
    assert "Python" in alignment["already_demonstrated"]
    assert "Linux" in alignment["already_demonstrated"]


def test_suggest_resume_customization_french_resume_end_to_end():
    """Verify that Suggest Resume Customization returns non-empty demonstrated skills and suggestions for French jobs."""
    from src.app.database import SessionLocal
    from src.app.models import Resume, Job, User
    from src.app.repositories.jobs import get_job_skills

    db = SessionLocal()
    try:
        # Load real French resume
        resume = db.query(Resume).filter_by(id=23).first()
        if not resume:
            resume = db.query(Resume).filter_by(id=30).first()
        if not resume:
            resume = db.query(Resume).filter(
                (Resume.filename.ilike("%fr.pdf") | Resume.title.ilike("%french%") | Resume.filename.ilike("%master_professional_resume%"))
            ).first()

        assert resume is not None, "Resume 23 / 30 / French resume must exist in database"
        user = resume.user

        # Test against Job 1 (Infrastructure & Virtualization)
        job1 = db.query(Job).filter_by(id=1).first()
        assert job1 is not None, "Job 1 must exist in test database"
        skills1 = get_job_skills(db, job1.id)

        analysis1 = analyze_resume_alignment(job1, skills1, resume, user=user)
        assert len(analysis1["already_demonstrated"]) >= 5, (
            f"Expected at least 5 demonstrated skills for Job 1, got {analysis1['already_demonstrated']}"
        )
        assert any("cloud" in s.lower() for s in analysis1["already_demonstrated"]), "Cloud skills should be matched"
        assert any("r" in s.lower() and "seaux" in s.lower() for s in analysis1["already_demonstrated"]) or any("devops" in s.lower() for s in analysis1["already_demonstrated"]), "DevOps/Networking skills should be matched"

        # Test against Job 466 (SOC Analyst - Stage)
        job466 = db.query(Job).filter_by(id=466).first()
        if job466:
            skills466 = get_job_skills(db, job466.id)
            analysis466 = analyze_resume_alignment(job466, skills466, resume, user=user)
            assert len(analysis466["already_demonstrated"]) > 0, (
                f"Expected non-empty demonstrated skills for Job 466, got {analysis466['already_demonstrated']}"
            )
            assert any(s in analysis466["already_demonstrated"] for s in ["SOC", "Cybersecurity", "Networking", "Cloud Computing", "AI", "Analytical Thinking", "C"])
    finally:
        db.close()

