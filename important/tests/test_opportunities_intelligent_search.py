from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, Company, Country, Job
from src.app.repositories.jobs import list_jobs
from src.app.services.opportunities_search import (
    prepare_search_plan,
    calculate_job_relevance,
    normalize_search_text,
    unaccent,
)


@pytest.fixture
def search_db_env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Countries
        fr = Country(id=1, name="France", code="FR")
        de = Country(id=2, name="Germany", code="DE")
        us = Country(id=3, name="United States", code="US")
        ma = Country(id=4, name="Morocco", code="MA")
        session.add_all([fr, de, us, ma])

        # Companies
        sopra = Company(id=1, name="Sopra Steria", website_url="https://soprasteria.com", active=True)
        siemens = Company(id=2, name="Siemens", website_url="https://siemens.com", active=True)
        google = Company(id=3, name="Google", website_url="https://google.com", active=True)
        session.add_all([sopra, siemens, google])
        session.flush()

        # Jobs dataset designed to test relevance tiers, multilingual semantics, accents, and filters
        jobs = [
            # Job 1: Exact title match "Internship"
            Job(
                id=1,
                company_id=3,
                country_id=3,
                title="Internship",
                description="General internship program in Mountain View.",
                job_url="https://test.corp/jobs/1",
                employment_type="internship",
                remote_type="onsite",
                active=True,
                posted_at=now - timedelta(days=5),
                discovered_at=now - timedelta(days=5),
                created_at=now,
                updated_at=now,
            ),
            # Job 2: Title phrase match "Software Engineering Internship"
            Job(
                id=2,
                company_id=3,
                country_id=3,
                title="Software Engineering Internship",
                description="Build scalable distributed cloud services.",
                job_url="https://test.corp/jobs/2",
                employment_type="internship",
                remote_type="hybrid",
                active=True,
                posted_at=now - timedelta(days=3),
                discovered_at=now - timedelta(days=3),
                created_at=now,
                updated_at=now,
            ),
            # Job 3: French Internship "Stage Développeur Python (H/F)"
            Job(
                id=3,
                company_id=1,
                country_id=1,
                title="Stage Développeur Python (H/F)",
                description="Stage de fin d'études au sein de nos équipes R&D.",
                job_url="https://test.corp/jobs/3",
                employment_type="internship",
                remote_type="hybrid",
                active=True,
                posted_at=now - timedelta(days=4),
                discovered_at=now - timedelta(days=4),
                created_at=now,
                updated_at=now,
            ),
            # Job 4: French Internship with Stagiaire "Stagiaire Cybersécurité"
            Job(
                id=4,
                company_id=1,
                country_id=1,
                title="Stagiaire Cybersécurité",
                description="Analyse des vulnérabilités et monitoring SOC.",
                job_url="https://test.corp/jobs/4",
                employment_type="internship",
                remote_type="onsite",
                active=True,
                posted_at=now - timedelta(days=2),
                discovered_at=now - timedelta(days=2),
                created_at=now,
                updated_at=now,
            ),
            # Job 5: German Internship "Praktikum Softwareentwicklung Cloud"
            Job(
                id=5,
                company_id=2,
                country_id=2,
                title="Praktikum Softwareentwicklung Cloud",
                description="Entwicklung innovativer Cloud-Lösungen für Automatisierung.",
                job_url="https://test.corp/jobs/5",
                employment_type="internship",
                remote_type="hybrid",
                active=True,
                posted_at=now - timedelta(days=1),
                discovered_at=now - timedelta(days=1),
                created_at=now,
                updated_at=now,
            ),
            # Job 6: Description-ONLY match for "internship" (Posted very recently!)
            # Title is "Senior Infrastructure Architect", but description mentions "we also offer internship programs"
            Job(
                id=6,
                company_id=1,
                country_id=1,
                title="Senior Infrastructure Architect",
                description="Leading enterprise cloud migration. Our team also supports summer internship projects.",
                job_url="https://test.corp/jobs/6",
                employment_type="full_time",
                remote_type="remote",
                active=True,
                posted_at=now - timedelta(minutes=10),  # Most recently posted!
                discovered_at=now - timedelta(minutes=10),
                created_at=now,
                updated_at=now,
            ),
            # Job 7: French Gendered Title "Développeuse Fullstack"
            Job(
                id=7,
                company_id=1,
                country_id=1,
                title="Développeuse Fullstack",
                description="Conception et développement d'applications web modernes en React et Node.",
                job_url="https://test.corp/jobs/7",
                employment_type="full_time",
                remote_type="remote",
                active=True,
                posted_at=now - timedelta(days=6),
                discovered_at=now - timedelta(days=6),
                created_at=now,
                updated_at=now,
            ),
            # Job 8: German Gendered Title "Software-Entwicklerin (w/m/d)"
            Job(
                id=8,
                company_id=2,
                country_id=2,
                title="Software-Entwicklerin (w/m/d)",
                description="Entwicklung moderner Microservices mit Python und Docker.",
                job_url="https://test.corp/jobs/8",
                employment_type="full_time",
                remote_type="hybrid",
                active=True,
                posted_at=now - timedelta(days=7),
                discovered_at=now - timedelta(days=7),
                created_at=now,
                updated_at=now,
            ),
            # Job 9: Inactive Job (Should be filtered out when active_only=True)
            Job(
                id=9,
                company_id=3,
                country_id=3,
                title="Internship in AI Research",
                description="Expired listing.",
                job_url="https://test.corp/jobs/9",
                employment_type="internship",
                remote_type="onsite",
                active=False,
                posted_at=now,
                discovered_at=now,
                created_at=now,
                updated_at=now,
            ),
            # Job 10: German Werkstudent "Werkstudent IT-Sicherheit"
            Job(
                id=10,
                company_id=2,
                country_id=2,
                title="Werkstudent IT-Sicherheit",
                description="Unterstützung bei Penetrationstests und Sicherheitsüberprüfungen.",
                job_url="https://test.corp/jobs/10",
                employment_type="internship",
                remote_type="remote",
                active=True,
                posted_at=now - timedelta(days=3),
                discovered_at=now - timedelta(days=3),
                created_at=now,
                updated_at=now,
            ),
        ]
        session.add_all(jobs)
        session.commit()

    return session_factory


# ===========================================================================
# 1. Title vs Description Priority (Core Requirement)
# ===========================================================================

def test_title_vs_description_priority(search_db_env):
    """
    A job with the search term in the TITLE must decisively outrank
    a job where the term appears only in the DESCRIPTION, even if the description-only
    job was posted much more recently.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="internship")

        assert total >= 5
        result_ids = [j.id for j in results]

        # Job 1, 2, 3, 4, 5 all have "internship" / "stage" / "praktikum" in their TITLES.
        # Job 6 only has "internship" mentioned once in its DESCRIPTION, but has the newest posted_at.
        # Job 6 MUST rank behind all title matches!
        assert 6 in result_ids
        idx_desc_only = result_ids.index(6)

        for title_job_id in [1, 2, 3, 4, 5]:
            if title_job_id in result_ids:
                idx_title = result_ids.index(title_job_id)
                assert idx_title < idx_desc_only, (
                    f"Title match Job #{title_job_id} (rank {idx_title}) should rank ahead "
                    f"of description-only match Job #6 (rank {idx_desc_only})"
                )


def test_exact_title_match_ranks_first(search_db_env):
    """
    Job #1 has the exact title "Internship". It should rank above partial title matches.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="internship")
        assert len(results) > 0
        # Job #1 (exact title match) must be first
        assert results[0].id == 1


# ===========================================================================
# 2. Multilingual Search (English, French, German)
# ===========================================================================

def test_multilingual_search_english_to_french_and_german(search_db_env):
    """
    Searching English 'internship' must prominently surface:
    - French 'Stage Développeur Python'
    - French 'Stagiaire Cybersécurité'
    - German 'Praktikum Softwareentwicklung Cloud'
    - German 'Werkstudent IT-Sicherheit'
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="internship")
        result_ids = [j.id for j in results]

        # All multilingual equivalents must be returned
        assert 3 in result_ids, "French 'Stage' job should be found"
        assert 4 in result_ids, "French 'Stagiaire' job should be found"
        assert 5 in result_ids, "German 'Praktikum' job should be found"
        assert 10 in result_ids, "German 'Werkstudent' job should be found"


def test_multilingual_search_french_stage_to_english_and_german(search_db_env):
    """
    Searching French 'stage' must surface:
    - French stages (#3, #4)
    - English internships (#1, #2)
    - German Praktikum (#5)
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="stage")
        result_ids = [j.id for j in results]

        assert 3 in result_ids
        assert 4 in result_ids
        assert 1 in result_ids
        assert 2 in result_ids
        assert 5 in result_ids


def test_multilingual_search_german_praktikum(search_db_env):
    """
    Searching German 'Praktikum' must surface German Praktikum, English internships, and French stages.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="Praktikum")
        result_ids = [j.id for j in results]

        assert 5 in result_ids, "German Praktikum must be found"
        assert 1 in result_ids, "English Internship must be found"
        assert 3 in result_ids, "French Stage must be found"


def test_multilingual_cybersecurity_across_languages(search_db_env):
    """
    Searching 'cybersecurity' should find French 'Stagiaire Cybersécurité' and German 'Werkstudent IT-Sicherheit'.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="cybersecurity")
        result_ids = [j.id for j in results]

        assert 4 in result_ids  # French Stagiaire Cybersécurité
        assert 10 in result_ids  # German Werkstudent IT-Sicherheit


# ===========================================================================
# 3. Normalization (Accents, Diacritics, Gendered Forms, Compounds)
# ===========================================================================

def test_accent_and_diacritic_normalization(search_db_env):
    """
    Searching unaccented 'developpeur' or 'cybersecurite' must find accented 'Développeur' and 'Cybersécurité'.
    """
    with search_db_env() as session:
        # 1. Unaccented search for developer
        res_dev, total_dev = list_jobs(session, search="developpeur")
        dev_ids = [j.id for j in res_dev]
        assert 3 in dev_ids  # Stage Développeur Python
        assert 7 in dev_ids  # Développeuse Fullstack

        # 2. Unaccented search for cybersecurity
        res_sec, total_sec = list_jobs(session, search="cybersecurite")
        sec_ids = [j.id for j in res_sec]
        assert 4 in sec_ids  # Stagiaire Cybersécurité


def test_gendered_forms_french_and_german(search_db_env):
    """
    Searching masculine 'développeur' or English 'developer' finds feminine 'Développeuse' and German 'Software-Entwicklerin'.
    Searching German 'Entwickler' finds 'Software-Entwicklerin'.
    """
    with search_db_env() as session:
        # Search developer finds French Développeuse (#7) and German Entwicklerin (#8)
        res_dev, total_dev = list_jobs(session, search="developer")
        dev_ids = [j.id for j in res_dev]
        assert 7 in dev_ids
        assert 8 in dev_ids

        # Search German Entwickler finds Software-Entwicklerin
        res_de, total_de = list_jobs(session, search="Entwickler")
        de_ids = [j.id for j in res_de]
        assert 8 in de_ids


def test_preserve_displayed_job_title_in_objects(search_db_env):
    """
    The original raw job title in the Job model must NOT be overwritten or mutated.
    """
    with search_db_env() as session:
        results, _ = list_jobs(session, search="stage")
        for j in results:
            if j.id == 3:
                assert j.title == "Stage Développeur Python (H/F)"
            elif j.id == 7:
                assert j.title == "Développeuse Fullstack"


# ===========================================================================
# 4. Filters Combined with Search
# ===========================================================================

def test_search_combined_with_country_filter(search_db_env):
    """
    Search 'internship' + country France (#1) returns ONLY French internships.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, country_id=1, search="internship")
        assert total >= 2
        for j in results:
            assert j.country_id == 1


def test_search_combined_with_remote_filter(search_db_env):
    """
    Search 'internship' + remote_type 'remote' returns only remote internships.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, remote_type="remote", search="internship")
        for j in results:
            assert j.remote_type == "remote"


def test_search_combined_with_company_filter(search_db_env):
    """
    Search 'internship' + company Siemens (#2) returns only Siemens jobs.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, company_id=2, search="internship")
        for j in results:
            assert j.company_id == 2


def test_active_only_filter_respected(search_db_env):
    """
    Inactive Job #9 (Internship in AI Research, active=False) must NOT appear when active_only=True.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="internship", active_only=True)
        result_ids = [j.id for j in results]
        assert 9 not in result_ids


# ===========================================================================
# 5. Pagination After Ranking
# ===========================================================================

def test_pagination_after_ranking(search_db_env):
    """
    Ranking happens before pagination: Page 1 (limit=2) must contain the highest
    relevance jobs, and Page 2 (skip=2, limit=2) contains the next tier.
    """
    with search_db_env() as session:
        page1, total1 = list_jobs(session, search="internship", skip=0, limit=2)
        page2, total2 = list_jobs(session, search="internship", skip=2, limit=2)

        assert total1 == total2
        assert len(page1) == 2
        assert len(page2) == 2

        # Disjoint sets
        page1_ids = [j.id for j in page1]
        page2_ids = [j.id for j in page2]
        assert set(page1_ids).isdisjoint(set(page2_ids))

        # The exact title match (Job #1) must be in Page 1!
        assert 1 in page1_ids
        # The description-only match (Job #6) must NOT be in Page 1!
        assert 6 not in page1_ids


# ===========================================================================
# 6. Edge Cases: Empty Queries, No-Result Queries, Stable Sorting
# ===========================================================================

def test_empty_query_preserves_default_date_ordering(search_db_env):
    """
    When search is empty or whitespace, list_jobs returns all active jobs ordered
    by posted_at desc without error.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="")
        assert total >= 8
        # Ensure ordered by posted_at descending
        for i in range(len(results) - 1):
            t1 = results[i].posted_at or results[i].discovered_at
            t2 = results[i + 1].posted_at or results[i + 1].discovered_at
            if t1 and t2:
                assert t1 >= t2


def test_no_results_query(search_db_env):
    """
    A search for a non-existent term returns 0 results cleanly.
    """
    with search_db_env() as session:
        results, total = list_jobs(session, search="xyznonexistentkeyword999")
        assert total == 0
        assert len(results) == 0


def test_stable_deterministic_ranking(search_db_env):
    """
    Calling list_jobs multiple times with the same query produces identical rankings.
    """
    with search_db_env() as session:
        run1, _ = list_jobs(session, search="internship")
        run2, _ = list_jobs(session, search="internship")
        assert [j.id for j in run1] == [j.id for j in run2]
