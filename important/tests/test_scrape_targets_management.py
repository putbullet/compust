from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.models import Company, ScrapeTarget


def test_scrape_target_crud(client: TestClient, db_session: Session) -> None:
    # 1. Ensure test company exists
    company = db_session.query(Company).first()
    assert company is not None

    # 2. Create Scrape Target
    target_payload = {
        "company_id": company.id,
        "url": "https://example.com/careers/jobs",
        "type": "generic_html",
        "active": True,
    }
    create_res = client.post("/api/v1/scrape-targets", json=target_payload)
    assert create_res.status_code == 201
    created_target = create_res.json()
    target_id = created_target["id"]
    assert created_target["url"] == "https://example.com/careers/jobs"
    assert created_target["type"] == "generic_html"
    assert created_target["active"] is True

    # 3. Retrieve target
    get_res = client.get(f"/api/v1/scrape-targets/{target_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == target_id

    # 4. Update target
    update_res = client.put(
        f"/api/v1/scrape-targets/{target_id}",
        json={"url": "https://example.com/api/v2/jobs", "type": "capgemini_json"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["url"] == "https://example.com/api/v2/jobs"
    assert update_res.json()["type"] == "capgemini_json"

    # 5. Toggle target active
    toggle_res = client.patch(f"/api/v1/scrape-targets/{target_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["active"] is False

    # 6. Delete target
    del_res = client.delete(f"/api/v1/scrape-targets/{target_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    not_found = client.get(f"/api/v1/scrape-targets/{target_id}")
    assert not_found.status_code == 404
