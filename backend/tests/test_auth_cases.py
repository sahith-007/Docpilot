from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import User
from app.db.session import SessionLocal
from app.main import app


def test_register_success_and_password_is_hashed():
    email = f"doctor-{uuid4().hex[:8]}@docpilot.health"
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "full_name": "Dr. Lina Brooks",
                "email": email,
                "password": "secure-demo-pass",
                "specialty": "Internal Medicine",
            },
        )

    assert response.status_code == 201
    assert response.json()["access_token"]
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        assert user.password_hash != "secure-demo-pass"
        assert user.password_hash.startswith("pbkdf2_sha256$")


def test_duplicate_registration_fails_cleanly():
    email = f"doctor-{uuid4().hex[:8]}@docpilot.health"
    payload = {
        "full_name": "Dr. Duplicate",
        "email": email,
        "password": "secure-demo-pass",
        "specialty": "Hospital Medicine",
    }
    with TestClient(app) as client:
        first = client.post("/auth/register", json=payload)
        second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_assigned_patient_filtering_and_case_access():
    with TestClient(app) as client:
        login = client.post(
            "/auth/login",
            json={"email": "sahith@docpilot.health", "password": "demo-clinical"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        cases = client.get("/cases", headers=headers)
        forbidden_case = client.get("/cases/case-singh-003", headers=headers)
        assigned_case = client.get("/cases/case-lee-006", headers=headers)

    assert cases.status_code == 200
    assert {case["id"] for case in cases.json()} == {
        "case-lee-006",
        "case-ramirez-007",
        "case-kim-010",
    }
    assert forbidden_case.status_code == 404
    assert assigned_case.status_code == 200
