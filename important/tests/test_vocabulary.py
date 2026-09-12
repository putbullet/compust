from src.app.scraper.vocabulary import (
    normalize_employment_type,
    normalize_remote_type,
    normalize_location,
    normalize_skills,
)


def test_normalize_employment_type() -> None:
    assert normalize_employment_type("CDI") == "full_time"
    assert normalize_employment_type("Contrat à durée indéterminée") == "full_time"
    assert normalize_employment_type("Full-time position") == "full_time"
    assert normalize_employment_type("CDD") == "contract"
    assert normalize_employment_type("Fixed-term contract") == "contract"
    assert normalize_employment_type("Stage PFE") == "internship"
    assert normalize_employment_type("Internship 6 months") == "internship"
    assert normalize_employment_type("Temps partiel") == "part_time"
    assert normalize_employment_type("Freelance") == "freelance"
    assert normalize_employment_type(None) is None
    assert normalize_employment_type("") is None


def test_normalize_remote_type() -> None:
    assert normalize_remote_type("100% Remote") == "remote"
    assert normalize_remote_type("Télétravail complet") == "remote"
    assert normalize_remote_type("Hybride (2j sur site)") == "hybrid"
    assert normalize_remote_type("Flexible / Hybrid") == "hybrid"
    assert normalize_remote_type("Sur site uniquement") == "onsite"
    assert normalize_remote_type("On-site presence required") == "onsite"
    assert normalize_remote_type(None) is None


def test_normalize_location() -> None:
    loc1 = normalize_location("Casablanca, Maroc")
    assert loc1["city"] == "Casablanca"
    assert loc1["country"] == "Morocco"

    loc2 = normalize_location("Technopolis, Rabat")
    assert loc2["city"] in ["Technopolis", "Rabat"]
    assert loc2["country"] == "Morocco"

    loc3 = normalize_location("Paris, France")
    assert loc3["city"] == "Paris"
    assert loc3["country"] == "France"

    loc_empty = normalize_location(None)
    assert loc_empty["city"] is None
    assert loc_empty["country"] is None


def test_normalize_skills() -> None:
    raw = ["react.js", "React", "python3", "FASTAPI", "docker-compose", "k8s", "UNKNOWN_SKILL"]
    normalized = normalize_skills(raw)
    assert "React" in normalized
    assert "Python" in normalized
    assert "FastAPI" in normalized
    assert "Docker" in normalized
    assert "Kubernetes" in normalized
    assert "UNKNOWN_SKILL" in normalized
    # Ensure deduplication
    assert len([s for s in normalized if s == "React"]) == 1
