from fastapi.testclient import TestClient

from app.db.models import ReviewerFeedback
from app.db.session import SessionLocal
from app.main import app


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "demo-clinical"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _ask(client: TestClient, headers: dict[str, str], case_id: str = "case-lee-006") -> str:
    response = client.post(
        "/assistant/ask",
        headers=headers,
        json={
            "case_id": case_id,
            "question": "What evidence supports COPD exacerbation?",
            "max_evidence": 5,
        },
    )
    assert response.status_code == 200
    return response.json()["answer_id"]


def test_feedback_can_be_created_and_updated():
    with TestClient(app) as client:
        headers = _login(client, "sahith@docpilot.health")
        answer_id = _ask(client, headers)

        review = client.post(
            "/feedback",
            headers=headers,
            json={"answer_id": answer_id, "status": "review"},
        )
        accepted = client.post(
            "/feedback",
            headers=headers,
            json={"answer_id": answer_id, "status": "accepted"},
        )
        rejected = client.post(
            "/feedback",
            headers=headers,
            json={"answer_id": answer_id, "status": "rejected"},
        )

    assert review.status_code == 200
    assert review.json()["status"] == "review"
    assert review.json()["message"] == "Review saved"
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["message"] == "Accepted saved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["message"] == "Rejected saved"

    with SessionLocal() as db:
        rows = db.query(ReviewerFeedback).filter(ReviewerFeedback.answer_id == answer_id).all()
        assert len(rows) == 1
        assert rows[0].verdict == "rejected"


def test_feedback_legacy_verdict_request_still_updates_current_state():
    with TestClient(app) as client:
        headers = _login(client, "sahith@docpilot.health")
        answer_id = _ask(client, headers)

        response = client.post(
            "/feedback",
            headers=headers,
            json={
                "answer_id": answer_id,
                "verdict": "needs_review",
                "reason": "missing_evidence",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "review"
    assert response.json()["verdict"] == "needs_review"


def test_feedback_cannot_be_submitted_for_inaccessible_answer():
    with TestClient(app) as client:
        maya_headers = _login(client, "maya.chen@docpilot.health")
        answer_id = _ask(
            client,
            maya_headers,
            case_id="case-singh-003",
        )
        sahith_headers = _login(client, "sahith@docpilot.health")

        response = client.post(
            "/feedback",
            headers=sahith_headers,
            json={"answer_id": answer_id, "status": "accepted"},
        )

    assert response.status_code == 404
    with SessionLocal() as db:
        assert db.query(ReviewerFeedback).filter(ReviewerFeedback.answer_id == answer_id).count() == 0


def test_conversation_includes_latest_feedback_status():
    with TestClient(app) as client:
        headers = _login(client, "sahith@docpilot.health")
        answer_id = _ask(client, headers)
        saved = client.post(
            "/feedback",
            headers=headers,
            json={"answer_id": answer_id, "status": "review"},
        )
        assert saved.status_code == 200
        changed = client.post(
            "/feedback",
            headers=headers,
            json={"answer_id": answer_id, "status": "accepted"},
        )
        assert changed.status_code == 200

        conversation = client.get("/assistant/conversations/case-lee-006", headers=headers)

    assert conversation.status_code == 200
    assistant_messages = [
        message
        for message in conversation.json()["messages"]
        if message.get("answer_id") == answer_id
    ]
    assert assistant_messages
    assert assistant_messages[-1]["feedback_status"] == "accepted"
    assert assistant_messages[-1]["feedback_message"] == "Accepted saved"
    assert assistant_messages[-1]["feedback_updated_at"]

