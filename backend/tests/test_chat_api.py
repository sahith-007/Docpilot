from fastapi.testclient import TestClient

from app.main import app
from app.services.openai_client import AnswerDraft


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": "maya.chen@docpilot.health", "password": "demo-clinical"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_ask_returns_model_metadata_and_conversation_is_case_scoped():
    with TestClient(app) as client:
        headers = _auth_headers(client)

        first = client.post(
            "/assistant/ask",
            headers=headers,
            json={
                "case_id": "case-marlowe-001",
                "question": "What evidence supports heart failure as the main driver of dyspnea?",
                "max_evidence": 5,
            },
        )
        second = client.post(
            "/assistant/ask",
            headers=headers,
            json={
                "case_id": "case-ibarra-002",
                "question": "What evidence suggests diabetic foot infection without osteomyelitis?",
                "max_evidence": 5,
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["model"]
        assert first.json()["created_at"]
        assert first.json()["citations"]

        marlowe = client.get("/assistant/conversations/case-marlowe-001", headers=headers)
        ibarra = client.get("/assistant/conversations/case-ibarra-002", headers=headers)

        assert marlowe.status_code == 200
        assert ibarra.status_code == 200
        marlowe_text = " ".join(message["content"] for message in marlowe.json()["messages"])
        ibarra_text = " ".join(message["content"] for message in ibarra.json()["messages"])
        assert "heart failure" in marlowe_text.lower()
        assert "osteomyelitis" not in marlowe_text.lower()
        assert "osteomyelitis" in ibarra_text.lower()


def test_real_mode_uses_openai_model_without_demo_fallback(monkeypatch):
    from app.services import assistant as assistant_service

    def fake_generate_openai_answer(question, evidence, history):
        return AnswerDraft(
            answer=f"Mocked model answer for: {question}",
            confidence="high",
            limits=[],
        )

    monkeypatch.setattr(assistant_service.settings, "demo_mode", False)
    monkeypatch.setattr(assistant_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(assistant_service.settings, "openai_chat_model", "gpt-4.1-mini")
    monkeypatch.setattr(assistant_service, "generate_openai_answer", fake_generate_openai_answer)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        response = client.post(
            "/assistant/ask",
            headers=headers,
            json={
                "case_id": "case-singh-003",
                "question": "Why is orthostatic hypotension favored over arrhythmia for syncope?",
                "max_evidence": 5,
            },
        )
        conversation = client.get("/assistant/conversations/case-singh-003", headers=headers)

    assert response.status_code == 200
    assert response.json()["model"] == "gpt-4.1-mini"
    assert response.json()["model"] != "demo-local"
    assert response.json()["provider_used"] == "openai"
    assert conversation.status_code == 200
    assistant_messages = [
        message for message in conversation.json()["messages"] if message["role"] == "assistant"
    ]
    assert assistant_messages[-1]["model"] == "gpt-4.1-mini"


def test_real_mode_openai_failure_returns_clear_error(monkeypatch):
    from app.services import assistant as assistant_service
    from app.services.openai_client import OpenAIGenerationError
    from app.db.models import ClinicalAnswer, ClinicalQuestion
    from app.db.session import SessionLocal

    def fail_openai(question, evidence, history):
        raise OpenAIGenerationError("OpenAI request failed: test failure")

    monkeypatch.setattr(assistant_service.settings, "demo_mode", False)
    monkeypatch.setattr(assistant_service.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(assistant_service, "generate_openai_answer", fail_openai)
    question = "Why is orthostatic hypotension favored over arrhythmia for syncope?"

    with TestClient(app) as client:
        headers = _auth_headers(client)
        response = client.post(
            "/assistant/ask",
            headers=headers,
            json={
                "case_id": "case-singh-003",
                "question": question,
                "max_evidence": 5,
            },
        )

    assert response.status_code == 502
    assert response.json()["detail"]["type"] == "openai_error"
    with SessionLocal() as db:
        stored_question = db.query(ClinicalQuestion).filter(ClinicalQuestion.question == question).first()
        assert stored_question is None
        assert db.query(ClinicalAnswer).filter(ClinicalAnswer.model_name == "demo-local").count() == 0


def test_demo_mode_allows_demo_local_model(monkeypatch):
    from app.services import assistant as assistant_service

    monkeypatch.setattr(assistant_service.settings, "demo_mode", True)

    with TestClient(app) as client:
        headers = _auth_headers(client)
        response = client.post(
            "/assistant/ask",
            headers=headers,
            json={
                "case_id": "case-singh-003",
                "question": "Why is orthostatic hypotension favored over arrhythmia for syncope?",
                "max_evidence": 5,
            },
        )

    assert response.status_code == 200
    assert response.json()["model"] == "demo-local"
    assert response.json()["provider_used"] == "demo"


def test_debug_config_returns_safe_openai_state(monkeypatch):
    from app.api import debug

    monkeypatch.setattr(debug.settings, "demo_mode", False)
    monkeypatch.setattr(debug.settings, "openai_chat_model", "gpt-4.1-mini")
    monkeypatch.setattr(debug.settings, "openai_api_key", "test-key")

    with TestClient(app) as client:
        response = client.get("/debug/config")

    assert response.status_code == 200
    assert response.json() == {
        "demo_mode": False,
        "model": "gpt-4.1-mini",
        "openai_key_present": True,
    }
