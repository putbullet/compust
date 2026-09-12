from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, Job, JobSkill
from src.app.repositories.jobs import persist_candidates
from src.app.scraper.orange_parser import JobCandidate


def test_persist_candidates_adds_then_updates_without_duplicates() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    candidate = JobCandidate(
        title="Engineer <script>alert('xss')</script>",
        job_url="https://example.test/job/1",
        external_job_id="EXT-1",
        location="Casablanca",
        description="<p>Build systems</p><script>evil()</script>",
        employment_type="CDI",
        remote_type="Hybrid",
        department="Engineering",
        posted_at=datetime(2026, 9, 8),
        skills=["Python", "Python", "SQL"],
        salary_min=45000.0,
        salary_max=60000.0,
        salary_currency="MAD",
        salary_period="annual",
    )
    with factory() as session:
        assert persist_candidates(session, company_id=1, country_id=2, source="test", candidates=[candidate]) == (1, 0)
        candidate = JobCandidate(**{**candidate.__dict__, "title": "Senior Engineer"})
        assert persist_candidates(session, company_id=1, country_id=2, source="test", candidates=[candidate]) == (0, 1)
        jobs = session.scalars(select(Job)).all()
        skills = session.scalars(select(JobSkill)).all()
        assert len(jobs) == 1
        assert jobs[0].title == "Senior Engineer"
        assert jobs[0].salary_min == 45000.0
        assert jobs[0].salary_max == 60000.0
        assert jobs[0].salary_currency == "MAD"
        assert jobs[0].salary_period == "annual"
        assert "<script>" not in jobs[0].description
        assert "evil()" not in jobs[0].description
        assert "<p>Build systems</p>" in jobs[0].description
        assert {skill.skill for skill in skills} == {"Python", "SQL"}
    engine.dispose()
