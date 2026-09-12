from datetime import datetime
from src.app.matching.matcher import calculate_job_match
from src.app.models import Job, User, UserPreference, UserSkill


def test_calculate_job_match_scores_and_explanations() -> None:
    user = User(
        id=1,
        email="test@example.com",
        password_hash="hash",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        email_verified=True,
        is_active=True,
    )
    user.skills = [
        UserSkill(id=1, user_id=1, skill="Python"),
        UserSkill(id=2, user_id=1, skill="FastAPI"),
        UserSkill(id=3, user_id=1, skill="Docker"),
    ]
    user.preferences = UserPreference(
        id=1,
        user_id=1,
        preferred_work_mode="Hybrid",
        preferred_location="Casablanca",
        min_salary=15000.0,
        salary_currency="MAD",
    )

    # Job that strongly matches
    good_job = Job(
        id=10,
        company_id=1,
        country_id=1,
        title="Senior Python Backend Developer",
        location="Casablanca",
        job_url="https://example.test/jobs/10",
        remote_type="Hybrid",
        employment_type="CDI",
        active=True,
        discovered_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        salary_min=18000.0,
    )
    job_skills = ["Python", "FastAPI", "PostgreSQL"]

    match_good = calculate_job_match(good_job, job_skills, user)
    assert match_good.score >= 70
    assert any("Matched skills" in f for f in match_good.positive_factors)
    assert any("Matches work mode" in f for f in match_good.positive_factors)
    assert any("Matches location" in f for f in match_good.positive_factors)

    # Job that diverges
    mismatched_job = Job(
        id=11,
        company_id=1,
        country_id=1,
        title="Mobile Flutter Developer",
        location="Paris",
        job_url="https://example.test/jobs/11",
        remote_type="On-site",
        employment_type="CDI",
        active=True,
        discovered_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        salary_min=10000.0,
    )
    mismatch_skills = ["Flutter", "Dart"]

    match_bad = calculate_job_match(mismatched_job, mismatch_skills, user)
    assert match_bad.score < 50
    assert len(match_bad.missing_factors) > 0
