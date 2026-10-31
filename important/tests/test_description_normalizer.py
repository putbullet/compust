import pytest
from src.app.scraper.sanitizer import normalize_description
from src.app.schemas_job_assistant import ExternalJobInput


def test_greenhouse_double_encoded() -> None:
    raw = (
        "&amp;lt;p&amp;gt;At Acme Corp, we build &amp;lt;b&amp;gt;great tools&amp;lt;/b&amp;gt;.&amp;lt;/p&amp;gt;"
        "&amp;lt;ul&amp;gt;&amp;lt;li&amp;gt;5+ years Python&amp;lt;/li&amp;gt;&amp;lt;li&amp;gt;FastAPI &amp;amp; Docker&amp;lt;/li&amp;gt;&amp;lt;/ul&amp;gt;"
    )
    result = normalize_description(raw)
    assert "<p>" not in result
    assert "&lt;" not in result
    assert "At Acme Corp, we build great tools." in result
    assert "• 5+ years Python" in result
    assert "• FastAPI & Docker" in result


def test_workday_nested_lists() -> None:
    raw = (
        "<div>"
        "<h2>Role Overview</h2>"
        "<p>We are looking for a Senior Architect.</p>"
        "<h3>Qualifications:</h3>"
        "<ul>"
        "  <li>Engineering background"
        "    <ul>"
        "      <li>BS or MS in Computer Science</li>"
        "      <li>8+ years of production experience</li>"
        "    </ul>"
        "  </li>"
        "  <li>Strong communication skills</li>"
        "</ul>"
        "</div>"
    )
    result = normalize_description(raw)
    assert "<div>" not in result
    assert "<h2>" not in result
    assert "<ul>" not in result
    assert "<li>" not in result
    assert "Role Overview" in result
    assert "We are looking for a Senior Architect." in result
    assert "Qualifications:" in result
    assert "• Engineering background" in result
    assert "• BS or MS in Computer Science" in result
    assert "• 8+ years of production experience" in result
    assert "• Strong communication skills" in result


def test_lever_ats_format() -> None:
    raw = (
        "<div class=\"section-wrapper\">"
        "  <p><strong>About the Role:</strong></p>"
        "  <div>You will lead the backend team.<br><br>Daily responsibilities include:<br>"
        "  • Designing microservices<br>"
        "  • Mentoring juniors"
        "  </div>"
        "</div>"
    )
    result = normalize_description(raw)
    assert "<div" not in result
    assert "<p>" not in result
    assert "<br>" not in result
    assert "About the Role:" in result
    assert "You will lead the backend team." in result
    assert "Designing microservices" in result
    assert "Mentoring juniors" in result


def test_table_degradation() -> None:
    raw = (
        "<table>"
        "  <thead>"
        "    <tr><th>Track</th><th>Level</th><th>Location</th></tr>"
        "  </thead>"
        "  <tbody>"
        "    <tr><td>Core Backend</td><td>L5</td><td>Paris (Hybrid)</td></tr>"
        "    <tr><td>Site Reliability</td><td>L4</td><td>Remote EU</td></tr>"
        "  </tbody>"
        "</table>"
    )
    result = normalize_description(raw)
    assert "<table" not in result
    assert "<tr" not in result
    assert "<td" not in result
    assert "Track | Level | Location" in result
    assert "Core Backend | L5 | Paris (Hybrid)" in result
    assert "Site Reliability | L4 | Remote EU" in result


def test_script_style_injection_decomposed() -> None:
    raw = (
        "<script>window.pwned = true; document.cookie = 'stolen';</script>"
        "<style>body { display: none; background: #000; }</style>"
        "<noscript><p>Please enable JS</p></noscript>"
        "<iframe src=\"https://evil.com/exploit\"></iframe>"
        "<p>Legitimate job specification content.</p>"
    )
    result = normalize_description(raw)
    assert "pwned" not in result
    assert "stolen" not in result
    assert "display: none" not in result
    assert "evil.com" not in result
    assert "<iframe" not in result
    assert "<script" not in result
    assert "<style" not in result
    assert result == "Legitimate job specification content."


def test_french_accents_and_unicode() -> None:
    raw = (
        "<p>Société Générale recherche un <strong>Ingénieur d'études &amp; développement C++ / C#</strong>.</p>"
        "<p>Rémunération : 55 000 € à 70 000 € selon profil.</p>"
        "<ul>"
        "  <li>Maîtrise des algorithmes et structures de données</li>"
        "  <li>Expérience avérée en environnement distribué à haute disponibilité</li>"
        "</ul>"
    )
    result = normalize_description(raw)
    assert "Société Générale recherche un Ingénieur d'études & développement C++ / C#." in result
    assert "Rémunération : 55 000 € à 70 000 € selon profil." in result
    assert "• Maîtrise des algorithmes et structures de données" in result
    assert "• Expérience avérée en environnement distribué à haute disponibilité" in result


def test_plain_text_idempotence() -> None:
    plain_samples = [
        "Simple plain text job description without any HTML markup.",
        "Requirements:\n• 3+ years experience\n• Strong Python skills\n\nNice to have:\n• Kubernetes",
        "Salary: $120,000 - $160,000 / year + equity",
    ]
    for sample in plain_samples:
        assert normalize_description(sample) == sample


def test_angle_brackets_and_ampersand_in_plain_text() -> None:
    text = "Candidate must have C++ <3 years experience, Python > 3.10, and R&D background in algorithms (a < b and c > d)."
    result = normalize_description(text)
    assert result == text


def test_very_long_description() -> None:
    paragraphs = [
        f"<h3>Section {i}</h3><p>Paragraph {i} detailing technical expectations and requirements for engineer #{i}.</p>"
        for i in range(100)
    ]
    raw = "<div>" + "\n".join(paragraphs) + "</div>"
    result = normalize_description(raw)
    assert len(result) > 5000
    assert "<h3" not in result
    assert "<p>" not in result
    assert "Section 0" in result
    assert "Section 99" in result


def test_external_job_input_schema_normalizes_description() -> None:
    raw_html = "<p>We are searching for a senior leader.</p><ul><li>Leadership</li><li>Scalability</li></ul>" + (" " * 40)
    model = ExternalJobInput(
        target_role="Engineering Manager",
        job_description=raw_html,
    )
    assert "<p>" not in model.job_description
    assert "<ul>" not in model.job_description
    assert "<li>" not in model.job_description
    assert "We are searching for a senior leader." in model.job_description
    assert "• Leadership" in model.job_description
    assert "• Scalability" in model.job_description
