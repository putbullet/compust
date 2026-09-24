"""
test_sankey_pipeline.py
-----------------------
Regression suite for the Sankey/pipeline funnel data-correctness bug.

Root cause (now fixed): `get_sankey_pipeline` used to union the current status
with *every* historical to_status, making "reached_*" flags sticky.  Once an
application touched "accepted" it would stay counted as accepted even after
being changed back to "rejected".

These tests verify that the funnel always reflects *current* status only --
forward progressions, backward transitions, lateral moves, and the exact
originally-reported scenario.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.app.models import (
    Base,
    Company,
    Country,
    Job,
    User,
    UserApplication,
    UserApplicationHistory,
)
from src.app.repositories.applications import get_sankey_pipeline


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


def _make_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_db(session: Session) -> tuple[int, int]:
    """Seed a country, company, job and user. Returns (user_id, job_id)."""
    country = Country(id=1, name="Morocco", code="MA")
    company = Company(id=1, name="Acme Corp", website_url="https://acme.test", active=True)
    job = Job(
        id=1,
        company_id=1,
        country_id=1,
        title="Software Engineer",
        job_url="https://acme.test/jobs/1",
        active=True,
        discovered_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    user = User(
        id=1,
        email="candidate@test.com",
        password_hash="testhash",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add_all([country, company, job, user])
    session.commit()
    return user.id, job.id


def _make_app(
    session: Session,
    user_id: int,
    job_id: int,
    status: str,
    app_id: int,
    history: list | None = None,
) -> UserApplication:
    """
    Create a UserApplication with the given current status and history entries.

    ``history`` is a list of (from_status, to_status) tuples representing past
    transitions -- they simulate what get_sankey_pipeline used to (wrongly)
    rely on.  The fix must ignore these for funnel counting.
    """
    app = UserApplication(
        id=app_id,
        user_id=user_id,
        job_id=job_id,
        status=status,
        source="LinkedIn",
        priority="medium",
        created_at=NOW,
        updated_at=NOW,
    )
    session.add(app)
    session.flush()

    for from_s, to_s in (history or []):
        session.add(
            UserApplicationHistory(
                application_id=app.id,
                from_status=from_s,
                to_status=to_s,
                changed_at=NOW,
            )
        )

    session.commit()
    return app


def _link_val(data, src: str, tgt: str) -> int:
    """Return the value of a specific link in SankeyDataRead, or 0."""
    for link in data.links:
        if link.source == src and link.target == tgt:
            return link.value
    return 0


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------

@pytest.fixture()
def db_and_ids():
    """Provide a fresh in-memory DB session plus seeded (user_id, job_id)."""
    engine = _make_engine()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        user_id, job_id = _seed_db(session)
        yield session, user_id, job_id


# ------------------------------------------------------------------------------
# Test 1 -- No applications -> empty funnel
# ------------------------------------------------------------------------------

def test_empty_pipeline(db_and_ids):
    session, user_id, _ = db_and_ids
    data = get_sankey_pipeline(session, user_id)
    assert data.total == 0
    assert data.nodes == []
    assert data.links == []


# ------------------------------------------------------------------------------
# Test 2 -- Applied / no-answer / rejected / withdrawn (pre-interview)
# ------------------------------------------------------------------------------

def test_applied_goes_to_no_answer(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status="applied", app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert data.total == 1
    assert _link_val(data, "stage_applications", "stage_no_answer") == 1
    assert _link_val(data, "stage_applications", "stage_1st_interview") == 0


def test_no_answer_status(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status="no_answer", app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_applications", "stage_no_answer") == 1


def test_rejected_before_interview(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status="rejected", app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_applications", "stage_rejected_init") == 1
    assert _link_val(data, "stage_applications", "stage_1st_interview") == 0


def test_withdrawn_before_interview(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status="withdrawn", app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_applications", "stage_withdrawn_init") == 1


# ------------------------------------------------------------------------------
# Test 3 -- Forward progression through each stage
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("status,expected_src,expected_tgt", [
    ("1st_interview",   "stage_applications",   "stage_1st_interview"),
    ("interviewing",    "stage_applications",   "stage_1st_interview"),
    ("2nd_interview",   "stage_1st_interview",  "stage_2nd_interview"),
    ("3rd_interview",   "stage_2nd_interview",  "stage_3rd_interview"),
    ("final_interview", "stage_3rd_interview",  "stage_4th_interview"),
    ("offer",           "stage_4th_interview",  "stage_offers"),
    ("accepted",        "stage_offers",         "stage_accepted"),
])
def test_forward_stage_flow(db_and_ids, status, expected_src, expected_tgt):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status=status, app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, expected_src, expected_tgt) == 1, (
        f"Expected link {expected_src} -> {expected_tgt} for status={status!r}, "
        f"links: {[(l.source, l.target, l.value) for l in data.links]}"
    )


# ------------------------------------------------------------------------------
# Test 4 -- THE REPORTED BUG: rejected -> accepted -> rejected
# ------------------------------------------------------------------------------

def test_backward_accepted_to_rejected_bug(db_and_ids):
    """
    Exact scenario from the bug report:
      1. Status set to Accepted   -> funnel must show it as accepted
      2. Status changed to Rejected -> funnel must now show it as rejected,
                                       NOT still accepted.
    """
    session, user_id, job_id = db_and_ids

    # Step 1: application is currently "accepted"
    _make_app(
        session, user_id, job_id, status="accepted", app_id=1,
        history=[
            (None,            "applied"),
            ("applied",       "1st_interview"),
            ("1st_interview", "2nd_interview"),
            ("2nd_interview", "offer"),
            ("offer",         "accepted"),
        ],
    )
    data_accepted = get_sankey_pipeline(session, user_id)
    assert _link_val(data_accepted, "stage_offers", "stage_accepted") == 1, (
        "Application at 'accepted' must flow to stage_accepted"
    )
    assert _link_val(data_accepted, "stage_applications", "stage_rejected_init") == 0

    # Step 2: status is changed back to "rejected"
    app = session.get(UserApplication, 1)
    app.status = "rejected"
    session.add(
        UserApplicationHistory(
            application_id=1,
            from_status="accepted",
            to_status="rejected",
            changed_at=NOW,
        )
    )
    session.commit()

    data_rejected = get_sankey_pipeline(session, user_id)

    # Must NOT appear as accepted any more
    assert _link_val(data_rejected, "stage_offers", "stage_accepted") == 0, (
        "After reverting to 'rejected', the funnel must not count the app in "
        "stage_accepted. The history-union bug would keep it there."
    )
    # Must appear as rejected at initial screening
    assert _link_val(data_rejected, "stage_applications", "stage_rejected_init") == 1, (
        "After reverting to 'rejected', funnel must route to stage_rejected_init"
    )


# ------------------------------------------------------------------------------
# Test 5 -- Lateral downgrade: 2nd_interview -> withdrawn
# ------------------------------------------------------------------------------

def test_lateral_2nd_interview_to_withdrawn(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(
        session, user_id, job_id, status="withdrawn", app_id=1,
        history=[
            (None,            "applied"),
            ("applied",       "1st_interview"),
            ("1st_interview", "2nd_interview"),
            ("2nd_interview", "withdrawn"),
        ],
    )
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_applications", "stage_withdrawn_init") == 1
    assert _link_val(data, "stage_applications", "stage_1st_interview") == 0
    assert _link_val(data, "stage_1st_interview", "stage_2nd_interview") == 0


# ------------------------------------------------------------------------------
# Test 6 -- 3rd_interview -> rejected
# ------------------------------------------------------------------------------

def test_3rd_interview_to_rejected(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(
        session, user_id, job_id, status="rejected", app_id=1,
        history=[
            (None,            "applied"),
            ("applied",       "1st_interview"),
            ("1st_interview", "2nd_interview"),
            ("2nd_interview", "3rd_interview"),
            ("3rd_interview", "rejected"),
        ],
    )
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_applications", "stage_rejected_init") == 1
    assert _link_val(data, "stage_2nd_interview", "stage_3rd_interview") == 0


# ------------------------------------------------------------------------------
# Test 7 -- In-progress states
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("status,expected_link", [
    ("1st_interview",   ("stage_1st_interview", "stage_in_progress_1st")),
    ("interviewing",    ("stage_1st_interview", "stage_in_progress_1st")),
    ("2nd_interview",   ("stage_2nd_interview", "stage_in_progress_2nd")),
    ("final_interview", ("stage_4th_interview", "stage_in_progress_final")),
])
def test_in_progress_states(db_and_ids, status, expected_link):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status=status, app_id=1)
    data = get_sankey_pipeline(session, user_id)
    src, tgt = expected_link
    assert _link_val(data, src, tgt) == 1, (
        f"status={status!r} should produce link {src}->{tgt}. "
        f"Links: {[(l.source, l.target, l.value) for l in data.links]}"
    )


# ------------------------------------------------------------------------------
# Test 8 -- Pending offer state
# ------------------------------------------------------------------------------

def test_offer_pending_state(db_and_ids):
    session, user_id, job_id = db_and_ids
    _make_app(session, user_id, job_id, status="offer", app_id=1)
    data = get_sankey_pipeline(session, user_id)
    assert _link_val(data, "stage_4th_interview", "stage_offers") == 1
    assert _link_val(data, "stage_offers", "stage_pending_offer") == 1
    assert _link_val(data, "stage_offers", "stage_accepted") == 0


# ------------------------------------------------------------------------------
# Test 9 -- Multiple applications, aggregate counts
# ------------------------------------------------------------------------------

def test_multiple_apps_aggregate_counts(db_and_ids):
    session, user_id, job_id = db_and_ids
    job2 = Job(
        id=2, company_id=1, country_id=1,
        title="Frontend Dev", job_url="https://acme.test/jobs/2",
        active=True, discovered_at=NOW, created_at=NOW, updated_at=NOW,
    )
    job3 = Job(
        id=3, company_id=1, country_id=1,
        title="Data Analyst", job_url="https://acme.test/jobs/3",
        active=True, discovered_at=NOW, created_at=NOW, updated_at=NOW,
    )
    session.add_all([job2, job3])
    session.commit()

    _make_app(session, user_id, job_id, status="accepted", app_id=1)
    _make_app(session, user_id, 2, status="rejected", app_id=2)
    _make_app(session, user_id, 3, status="1st_interview", app_id=3)

    data = get_sankey_pipeline(session, user_id)
    assert data.total == 3
    assert _link_val(data, "stage_offers", "stage_accepted") == 1
    assert _link_val(data, "stage_applications", "stage_rejected_init") == 1
    assert _link_val(data, "stage_1st_interview", "stage_in_progress_1st") == 1
    # Apps 1 (accepted path) + 3 (1st_interview) both enter 1st interview
    assert _link_val(data, "stage_applications", "stage_1st_interview") == 2


# ------------------------------------------------------------------------------
# Test 10 -- History must NEVER affect current-status routing (parametrized)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("past_statuses,current_status,expected_link", [
    (["accepted"],            "rejected",      ("stage_applications", "stage_rejected_init")),
    (["offer", "accepted"],   "applied",       ("stage_applications", "stage_no_answer")),
    (["2nd_interview"],       "no_answer",     ("stage_applications", "stage_no_answer")),
    (["final_interview"],     "withdrawn",     ("stage_applications", "stage_withdrawn_init")),
    ([],                      "1st_interview", ("stage_applications", "stage_1st_interview")),
])
def test_history_does_not_affect_routing(
    db_and_ids, past_statuses, current_status, expected_link
):
    """
    Regardless of what statuses appear in the history table, the funnel link
    must be determined only by current_status.
    """
    session, user_id, job_id = db_and_ids

    history_entries = []
    prev = None
    for s in past_statuses:
        history_entries.append((prev, s))
        prev = s
    if past_statuses:
        history_entries.append((past_statuses[-1], current_status))

    _make_app(
        session, user_id, job_id,
        status=current_status, app_id=1,
        history=history_entries,
    )
    data = get_sankey_pipeline(session, user_id)
    src, tgt = expected_link
    assert _link_val(data, src, tgt) == 1, (
        f"current_status={current_status!r}, past={past_statuses} -- "
        f"expected link {src}->{tgt}=1, got: "
        f"{[(l.source, l.target, l.value) for l in data.links]}"
    )
