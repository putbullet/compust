"""Tests for the enhanced multilingual generic extractor (Phase 2).

Covers:
- EN/FR/DE/ES section-label detection for description fields
- dt/dd field-grid extraction for ATS layouts
- Label/value sibling pair extraction
- Responsibilities + requirements section composition
- Corpus title validation flow
"""
from __future__ import annotations

import pytest
from src.app.services.generic_extractor import (
    extract_job_from_html,
    _extract_dt_dd_fields,
    _extract_label_value_pairs,
    _extract_section_by_label,
    _label_in,
    _norm,
    _DESCRIPTION_LABELS,
    _LOCATION_LABELS,
    _EMPLOYMENT_TYPE_LABELS,
    _RESPONSIBILITY_LABELS,
    _REQUIREMENT_LABELS,
)
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Unit tests for _norm() helper
# ---------------------------------------------------------------------------

def test_norm_strips_trailing_colon():
    assert _norm("Location:") == "location"
    assert _norm("Standort:") == "standort"


def test_norm_folds_accents():
    assert _norm("Stellenbeschreibung") == "stellenbeschreibung"
    assert _norm("Description du poste") == "description du poste"
    assert _norm("Responsabilités") == "responsabilites"
    assert _norm("Vos responsabilités") == "vos responsabilites"
    assert _norm("Localisation") == "localisation"
    assert _norm("Función") == "funcion"


def test_norm_collapses_whitespace():
    assert _norm("  job  description  ") == "job description"


def test_norm_strips_asterisk():
    assert _norm("Required Skills*") == "required skills"


# ---------------------------------------------------------------------------
# Unit tests for _label_in()
# ---------------------------------------------------------------------------

def test_label_in_english_description():
    assert _label_in("Job Description", _DESCRIPTION_LABELS)
    assert _label_in("About the Role", _DESCRIPTION_LABELS)
    assert _label_in("Key Responsibilities", _DESCRIPTION_LABELS)


def test_label_in_french_description():
    assert _label_in("Description du poste", _DESCRIPTION_LABELS)
    assert _label_in("Vos responsabilités", _DESCRIPTION_LABELS)
    assert _label_in("Le poste", _DESCRIPTION_LABELS)


def test_label_in_german_description():
    assert _label_in("Stellenbeschreibung", _DESCRIPTION_LABELS)
    assert _label_in("Ihre Aufgaben", _DESCRIPTION_LABELS)
    assert _label_in("Deine Aufgaben", _DESCRIPTION_LABELS)


def test_label_in_spanish_description():
    assert _label_in("Descripción del puesto", _DESCRIPTION_LABELS)
    assert _label_in("Responsabilidades", _DESCRIPTION_LABELS)


def test_label_in_location():
    assert _label_in("Location", _LOCATION_LABELS)
    assert _label_in("Lieu de travail", _LOCATION_LABELS)
    assert _label_in("Standort:", _LOCATION_LABELS)  # trailing colon stripped by _norm
    assert _label_in("Localizacao", _LOCATION_LABELS)


def test_label_in_employment_type():
    assert _label_in("Employment Type", _EMPLOYMENT_TYPE_LABELS)
    assert _label_in("Type de contrat", _EMPLOYMENT_TYPE_LABELS)
    assert _label_in("Vertragsart", _EMPLOYMENT_TYPE_LABELS)


# ---------------------------------------------------------------------------
# Unit tests for _extract_dt_dd_fields()
# ---------------------------------------------------------------------------

def test_extract_dt_dd_location_and_type():
    html = """
    <dl>
        <dt>Location</dt><dd>Paris, France</dd>
        <dt>Employment Type</dt><dd>Full-time</dd>
        <dt>Company</dt><dd>Acme Corp</dd>
    </dl>
    """
    soup = BeautifulSoup(html, "html.parser")
    fields = _extract_dt_dd_fields(soup)
    assert "location" in fields
    assert fields["location"] == "Paris, France"
    assert "employment type" in fields
    assert fields["employment type"] == "Full-time"


def test_extract_dt_dd_german_labels():
    html = """
    <dl>
        <dt>Standort:</dt><dd>Berlin, Deutschland</dd>
        <dt>Vertragsart:</dt><dd>Vollzeit</dd>
    </dl>
    """
    soup = BeautifulSoup(html, "html.parser")
    fields = _extract_dt_dd_fields(soup)
    assert "standort" in fields
    assert fields["standort"] == "Berlin, Deutschland"


# ---------------------------------------------------------------------------
# Unit tests for _extract_section_by_label()
# ---------------------------------------------------------------------------

def test_extract_section_by_label_english_heading():
    html = """
    <div>
        <h2>Job Description</h2>
        <p>We are looking for a talented engineer to join our team.</p>
        <p>You will work on cutting-edge projects across multiple domains.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_section_by_label(soup, _DESCRIPTION_LABELS, min_chars=20)
    assert result is not None
    assert "engineer" in result.lower()


def test_extract_section_by_label_german_heading():
    html = """
    <section>
        <h3>Stellenbeschreibung</h3>
        <p>Wir suchen einen erfahrenen Ingenieur für unser wachsendes Team.</p>
        <p>Sie werden an anspruchsvollen Projekten in verschiedenen Bereichen arbeiten.</p>
    </section>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_section_by_label(soup, _DESCRIPTION_LABELS, min_chars=30)
    assert result is not None
    assert "Ingenieur" in result or "ingenieur" in result.lower()


def test_extract_section_by_label_french_heading():
    html = """
    <div class="content">
        <h2>Description du poste</h2>
        <p>Nous recherchons un ingénieur logiciel expérimenté pour rejoindre notre équipe.</p>
        <p>Vous travaillerez sur des projets innovants dans un environnement agile.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_section_by_label(soup, _DESCRIPTION_LABELS, min_chars=30)
    assert result is not None
    assert "ingénieur" in result.lower() or "logiciel" in result.lower()


def test_extract_section_by_label_via_css_class():
    html = """
    <div id="job-description-section">
        We are seeking a passionate software developer with 3+ years of experience
        to build high-quality, scalable applications in a collaborative environment.
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = _extract_section_by_label(soup, _DESCRIPTION_LABELS, min_chars=50)
    assert result is not None
    assert "developer" in result.lower()


# ---------------------------------------------------------------------------
# End-to-end tests for extract_job_from_html()
# ---------------------------------------------------------------------------

WORKDAY_STYLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Software Engineer - Acme Corp</title>
    <meta property="og:site_name" content="Acme Corp" />
</head>
<body>
    <main>
        <h1>Software Engineer</h1>
        <dl>
            <dt>Location</dt><dd>Lyon, France</dd>
            <dt>Employment Type</dt><dd>Full-time</dd>
            <dt>Workplace Type</dt><dd>Hybrid</dd>
        </dl>
        <h2>Job Description</h2>
        <div>
            <p>We are looking for a skilled Software Engineer to join our engineering team.</p>
            <p>You will design, develop, and maintain high-quality software components.</p>
            <p>Collaborate with cross-functional teams across multiple time zones.</p>
        </div>
    </main>
</body>
</html>
"""

GERMAN_ATS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Softwareentwickler (m/w/d) - TechGmbH</title>
</head>
<body>
    <main>
        <h1>Softwareentwickler (m/w/d)</h1>
        <dl>
            <dt>Standort:</dt><dd>München, Deutschland</dd>
            <dt>Vertragsart:</dt><dd>Vollzeit</dd>
        </dl>
        <h2>Stellenbeschreibung</h2>
        <p>Wir suchen einen erfahrenen Softwareentwickler für unser wachsendes Team.</p>
        <p>Sie werden moderne Anwendungen entwickeln und an spannenden Projekten arbeiten.</p>
        <p>Agile Methoden und enge Zusammenarbeit sind für uns selbstverständlich.</p>
    </main>
</body>
</html>
"""

FRENCH_RESPONSIBILITIES_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Ingénieur Développement Logiciel - Société Anonyme</title>
</head>
<body>
    <div class="job-container">
        <h1>Ingénieur Développement Logiciel</h1>
        <dl>
            <dt>Lieu de travail</dt><dd>Paris, France</dd>
            <dt>Type de contrat</dt><dd>CDI</dd>
        </dl>
        <h3>Vos responsabilités</h3>
        <ul>
            <li>Concevoir et développer des solutions logicielles robustes</li>
            <li>Participer aux revues de code et aux réunions d'architecture</li>
            <li>Assurer la qualité et la maintenabilité du code</li>
        </ul>
        <h3>Profil recherché</h3>
        <ul>
            <li>5+ ans d'expérience en développement logiciel</li>
            <li>Maîtrise de Python, JavaScript ou Java</li>
        </ul>
    </div>
</body>
</html>
"""


def test_full_extraction_workday_english():
    result = extract_job_from_html(WORKDAY_STYLE_HTML, "https://acme.wd1.myworkdayjobs.com/jobs/123")
    assert result.title == "Software Engineer" or (result.title and "engineer" in result.title.lower())
    assert result.location == "Lyon, France"
    assert result.employment_type is not None
    assert result.remote_type == "Hybrid"
    assert result.description is not None
    assert len(result.description) > 50
    assert result.confidence in ("high", "medium")


def test_full_extraction_german_ats():
    result = extract_job_from_html(GERMAN_ATS_HTML, "https://jobs.techgmbh.de/stellen/123")
    assert result.title is not None
    assert "software" in result.title.lower() or "entwickler" in result.title.lower()
    assert result.location == "München, Deutschland"
    assert result.employment_type is not None
    assert result.description is not None
    assert len(result.description) > 50


def test_full_extraction_french_responsibilities():
    result = extract_job_from_html(FRENCH_RESPONSIBILITIES_HTML, "https://jobs.sa-company.fr/offres/123")
    assert result.title is not None
    assert result.location == "Paris, France"
    assert result.description is not None
    # Should pick up either the responsibilities section or requirements section
    assert len(result.description) > 50


def test_extraction_fallback_to_main_element():
    """When no section labels match, should fall back to <main> element."""
    html = """
    <html>
    <head><title>Data Analyst - BigData Co</title></head>
    <body>
        <main>
            <h1>Data Analyst</h1>
            <p>Company: BigData Co</p>
            <p>Location: London, UK</p>
            <p>We need a data analyst to help us make sense of our massive data pipeline.</p>
            <p>Requirements: 3+ years experience with SQL, Python, and BI tools.</p>
        </main>
    </body>
    </html>
    """
    result = extract_job_from_html(html, "https://careers.bigdata.com/jobs/456")
    assert result.title is not None
    assert "analyst" in result.title.lower() or "Data Analyst" in result.title
    assert result.description is not None
    assert len(result.description) > 50


def test_extraction_confidence_low_without_title_match():
    """When the page title is not in the 73k corpus, confidence should be low."""
    html = """
    <html>
    <head><title>Gröbzefelderian Wizard</title></head>
    <body>
        <main>
            <h1>Gröbzefelderian Wizard</h1>
            <p>Employer: Wacky Corp</p>
            <p>We are hiring a Gröbzefelderian Wizard to manage our portal of mystical energies.</p>
            <p>Requirements: Experience in portals, wizardry, and cloud computing.</p>
        </main>
    </body>
    </html>
    """
    result = extract_job_from_html(html, "https://wackycorp.com/jobs/999")
    assert result.confidence == "low"
    assert result.message is not None
