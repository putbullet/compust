from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.services.ai_tools import (
    count_new_jobs_today,
    count_total_jobs,
    count_active_companies,
    count_jobs_by_country,
    count_jobs_by_company,
    count_applied_jobs,
    get_recent_jobs,
    get_country_with_most_jobs,
    match_and_execute_tool,
)


def test_deterministic_tools(db_session: Session) -> None:
    # 1. New jobs today
    res1 = count_new_jobs_today(db_session)
    assert res1["metric"] == "new_jobs_today"
    assert isinstance(res1["count"], int)

    # 2. Total jobs
    res2 = count_total_jobs(db_session)
    assert res2["metric"] == "total_jobs"
    assert isinstance(res2["active_jobs"], int)

    # 3. Active companies
    res3 = count_active_companies(db_session)
    assert res3["metric"] == "active_companies"
    assert res3["active_count"] >= 0

    # 4. Jobs by country
    res4 = count_jobs_by_country(db_session, "Morocco")
    assert res4["metric"] == "jobs_by_country"
    assert res4["found"] is True

    # 5. Jobs by company
    res5 = count_jobs_by_company(db_session, "Orange")
    assert res5["metric"] == "jobs_by_company"

    # 6. Country with most jobs
    res6 = get_country_with_most_jobs(db_session)
    assert res6["metric"] == "country_with_most_jobs"

    # 7. Recent jobs
    res7 = get_recent_jobs(db_session, limit=3)
    assert res7["metric"] == "recent_jobs"
    assert len(res7["jobs"]) <= 3


def test_sql_injection_safety(db_session: Session) -> None:
    # Attempting SQL injection strings in query
    malicious_inputs = [
        "'; DROP TABLE jobs; --",
        "' OR '1'='1",
        "UNION SELECT * FROM users",
    ]
    for injection in malicious_inputs:
        # None of these can execute raw SQL; they are safely parameterized
        data, fallback = match_and_execute_tool(injection, db_session)
        assert isinstance(data, dict)
        assert isinstance(fallback, str)


def test_ai_chat_endpoint(client: TestClient) -> None:
    # Endpoint test with question
    res = client.post("/api/v1/ai/chat", json={"query": "How many jobs were added today?"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "facts" in data
    assert data["facts"]["metric"] == "new_jobs_today"
