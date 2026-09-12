from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.main import app
from src.app.models import Company, Country


def test_company_lifecycle(client: TestClient, db_session: Session) -> None:
    # 1. Ensure countries exist
    morocco = db_session.query(Country).filter(Country.code == "MA").first()
    france = db_session.query(Country).filter(Country.code == "FR").first()
    assert morocco is not None
    assert france is not None

    # 2. Create Company
    create_payload = {
        "name": "Test Global Corp",
        "website_url": "https://testglobal.com",
        "careers_url": "https://testglobal.com/careers",
        "active": True,
        "country_ids": [morocco.id],
    }
    create_res = client.post("/api/v1/companies", json=create_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    company_id = created_data["id"]
    assert created_data["name"] == "Test Global Corp"
    assert len(created_data["countries"]) == 1
    assert created_data["countries"][0]["code"] == "MA"

    # 3. Retrieve Company
    get_res = client.get(f"/api/v1/companies/{company_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Test Global Corp"

    # 4. Edit Company (Add France country link)
    update_payload = {
        "name": "Test Global Corp International",
        "country_ids": [morocco.id, france.id],
    }
    update_res = client.put(f"/api/v1/companies/{company_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Test Global Corp International"
    assert len(updated_data["countries"]) == 2
    codes = [c["code"] for c in updated_data["countries"]]
    assert "MA" in codes
    assert "FR" in codes

    # 5. Toggle active (Reversible deactivation)
    toggle_res = client.patch(f"/api/v1/companies/{company_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["active"] is False

    # Reactivate
    toggle_res2 = client.patch(f"/api/v1/companies/{company_id}/toggle")
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["active"] is True

    # 6. Safe Deletion (Default is deactivation)
    safe_del_res = client.delete(f"/api/v1/companies/{company_id}")
    assert safe_del_res.status_code == 200
    assert safe_del_res.json()["status"] == "deactivated"
    # Verify company still exists in DB but is inactive
    comp_check = client.get(f"/api/v1/companies/{company_id}")
    assert comp_check.status_code == 200
    assert comp_check.json()["active"] is False

    # 7. Hard Deletion (Requires confirm_hard_delete=true)
    hard_del_res = client.delete(f"/api/v1/companies/{company_id}?confirm_hard_delete=true")
    assert hard_del_res.status_code == 200
    assert hard_del_res.json()["status"] == "permanently_deleted"

    # Verify company no longer exists
    not_found_res = client.get(f"/api/v1/companies/{company_id}")
    assert not_found_res.status_code == 404
