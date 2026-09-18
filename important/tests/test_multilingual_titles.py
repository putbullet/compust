import pytest

from src.app.scraper.job_title_intelligence.normalizer import (
    normalize_title,
    unaccent,
    generate_normalized_variants,
)
from src.app.scraper.job_title_intelligence.index import get_job_title_index
from src.app.scraper.job_title_intelligence.matcher import (
    is_job_title_candidate,
    is_action_or_button_text,
)
from src.app.scraper.vocabulary import (
    normalize_employment_type,
    normalize_remote_type,
    normalize_location,
)


def test_unaccent():
    assert unaccent("développeur") == "developpeur"
    assert unaccent("Ingénieur Cybersécurité") == "Ingenieur Cybersecurite"
    assert unaccent("Überprüfung") == "Uberprufung"
    assert unaccent("système embarqué") == "systeme embarque"


def test_normalize_title_gender_markers():
    # French markers
    assert "ingénieur cybersécurité" in normalize_title("Ingénieur(e) Cybersécurité H/F")
    assert "ingenieur cybersecurite" in unaccent(normalize_title("Ingénieur(e) Cybersécurité H/F"))
    assert "développeur" in normalize_title("Développeur / Développeuse Python (F/H)")
    assert "consultant cloud" in normalize_title("Consultant(e) Cloud (H/F/D)")

    # German markers
    assert "softwareentwickler" in normalize_title("Softwareentwickler (m/w/d)")
    assert "data scientist" in normalize_title("Data Scientist (m/f/d)")
    assert "devops engineer" in normalize_title("DevOps Engineer (w/m/div)")


def test_generate_normalized_variants():
    variants = generate_normalized_variants("Ingénieur(e) Cybersécurité H/F")
    assert any("ingenieur" in v and "cybersecurite" in v for v in variants)


def test_multilingual_index_lookup():
    idx = get_job_title_index()

    # French exact & accented
    assert idx.contains_exact("ingénieur cybersécurité")
    assert idx.contains_exact("ingenieur cybersecurite")
    assert idx.contains_exact("stage ingénieur cybersécurité")
    assert idx.contains_exact("développeur full stack")
    assert idx.contains_exact("alternance data analyst")

    # German titles
    assert idx.contains_exact("softwareentwickler")
    assert idx.contains_exact("praktikant it-sicherheit")
    assert idx.contains_exact("werkstudent data science")

    # Canonical family verification
    match_french = idx.lookup_canonical("Ingénieur Cybersécurité")
    assert match_french is not None
    assert match_french.family == "cybersecurity"

    match_german = idx.lookup_canonical("Werkstudent Data Science")
    assert match_german is not None
    assert match_german.family == "data_ai"

    match_stage = idx.lookup_canonical("Stage Développeur Big Data")
    assert match_stage is not None
    assert match_stage.family in ("data_ai", "software_engineering")


def test_action_or_button_text_rejected():
    assert is_action_or_button_text("VOIR L'OFFRE")
    assert is_action_or_button_text("Voir l'offre")
    assert is_action_or_button_text("POSTULER")
    assert is_action_or_button_text("Apply Now")
    assert is_action_or_button_text("JETZT BEWERBEN")
    assert is_action_or_button_text("En savoir plus")
    assert is_action_or_button_text("Découvrir l'offre")

    # Legitimate titles must NOT be rejected
    assert not is_action_or_button_text("Ingénieur Cybersécurité")
    assert not is_action_or_button_text("Développeur Python")
    assert not is_action_or_button_text("Software Engineer")


def test_is_job_title_candidate():
    assert is_job_title_candidate("Ingénieur Cybersécurité (H/F)")
    assert is_job_title_candidate("Stage Développeur(se) Big Data")
    assert is_job_title_candidate("Softwareentwickler (m/w/d)")
    assert is_job_title_candidate("Full Stack Web Developer")

    # Should reject non-titles
    assert not is_job_title_candidate("VOIR L'OFFRE")
    assert not is_job_title_candidate("Nos métiers")
    assert not is_job_title_candidate("Rejoignez-nous")


def test_vocabulary_multilingual_employment_types():
    # Internships, stages, alternances, apprenticeships
    assert normalize_employment_type("Stage de fin d'études 6 mois") == "internship"
    assert normalize_employment_type("Alternance - Ingénieur Réseau") == "internship"
    assert normalize_employment_type("Contrat d'apprentissage 24 mois") == "internship"
    assert normalize_employment_type("Praktikum Software Development") == "internship"
    assert normalize_employment_type("Werkstudent Cyber Security") == "internship"

    # Permanent / CDI / Full-time
    assert normalize_employment_type("Contrat à durée indéterminée (CDI)") == "full_time"
    assert normalize_employment_type("Festanstellung in Vollzeit") == "full_time"
    assert normalize_employment_type("Full Time Position") == "full_time"

    # Contract / CDD
    assert normalize_employment_type("Contrat à durée déterminée (CDD)") == "contract"
    assert normalize_employment_type("Befristeter Vertrag") == "contract"


def test_vocabulary_multilingual_remote_types():
    assert normalize_remote_type("Poste ouvert au télétravail partiel") == "hybrid"
    assert normalize_remote_type("100% télétravail") == "remote"
    assert normalize_remote_type("Homeoffice möglich") == "hybrid"
    assert normalize_remote_type("Reines Homeoffice") == "remote"
    assert normalize_remote_type("Travail sur site") == "onsite"
    assert normalize_remote_type("Präsenz / Vor Ort") == "onsite"


def test_vocabulary_known_locations():
    loc1 = normalize_location("Poste basé à Colomiers (31)")
    assert loc1["city"] == "Colomiers"
    assert loc1["country"] == "France"

    loc2 = normalize_location("Courbevoie, Île-de-France")
    assert loc2["city"] == "Courbevoie"
    assert loc2["country"] == "France"

    loc3 = normalize_location("Cesson-Sévigné / Rennes")
    assert loc3["city"] in ("Cesson-Sévigné", "Rennes")
    assert loc3["country"] == "France"

    loc4 = normalize_location("Villeneuve-d'Ascq (Lille)")
    assert loc4["city"] in ("Villeneuve-d'Ascq", "Lille")
    assert loc4["country"] == "France"

    loc5 = normalize_location("Standort: Karlsruhe")
    assert loc5["city"] == "Karlsruhe"
    assert loc5["country"] == "Germany"
