import json

from fastapi.testclient import TestClient

from app.db.models import ClinicalCase, ClinicalQuestion, PatientAssignment, User
from app.db.session import SessionLocal
from app.main import app


DEMO_DOCTORS = {
    "maya.chen@docpilot.health",
    "sahith@docpilot.health",
    "vijay@docpilot.health",
    "ashish@docpilot.health",
}


def test_seed_creates_named_demo_doctors_with_valid_logins():
    with TestClient(app) as client:
        for email in DEMO_DOCTORS:
            response = client.post(
                "/auth/login",
                json={"email": email, "password": "demo-clinical"},
            )
            assert response.status_code == 200

    with SessionLocal() as db:
        doctors = db.query(User).filter(User.email.in_(DEMO_DOCTORS)).all()
        assert len(doctors) == 4
        assert {doctor.email for doctor in doctors} == DEMO_DOCTORS
        assert all(doctor.password_hash != "demo-clinical" for doctor in doctors)


def test_seed_assigns_at_least_three_patients_to_each_demo_doctor():
    with TestClient(app):
        pass

    with SessionLocal() as db:
        doctors = db.query(User).filter(User.email.in_(DEMO_DOCTORS)).all()
        for doctor in doctors:
            assigned_count = (
                db.query(PatientAssignment)
                .filter(PatientAssignment.doctor_id == doctor.id)
                .count()
            )
            assert assigned_count >= 3


def test_seed_creates_rich_synthetic_patients():
    with TestClient(app):
        pass

    with SessionLocal() as db:
        cases = db.query(ClinicalCase).all()
        assert len(cases) >= 10

        for clinical_case in cases:
            if not clinical_case.id.startswith("case-"):
                continue
            assert len(clinical_case.notes) >= 4
            assert len(json.loads(clinical_case.timeline_json)) >= 5
            assert len(json.loads(clinical_case.active_problems_json)) >= 3
            assert len(json.loads(clinical_case.labs_json)) + len(json.loads(clinical_case.vitals_json)) >= 5
            assert len(json.loads(clinical_case.suggested_questions_json)) >= 4


def test_seed_questions_are_case_specific_and_priya_chat_is_clean():
    with TestClient(app):
        pass

    with SessionLocal() as db:
        priya = db.get(ClinicalCase, "case-singh-003")
        elaine = db.get(ClinicalCase, "case-marlowe-001")
        jon = db.get(ClinicalCase, "case-ibarra-002")

        assert priya is not None
        assert elaine is not None
        assert jon is not None

        priya_questions = " ".join(json.loads(priya.suggested_questions_json)).lower()
        elaine_questions = " ".join(json.loads(elaine.suggested_questions_json)).lower()
        jon_questions = " ".join(json.loads(jon.suggested_questions_json)).lower()

        assert "orthostatic hypotension" in priya_questions
        assert "heart failure" not in priya_questions
        assert "dyspnea" not in priya_questions
        assert "heart failure" in elaine_questions
        assert "diabetic foot infection" in jon_questions

        priya_chat = (
            db.query(ClinicalQuestion)
            .filter(ClinicalQuestion.case_id == "case-singh-003")
            .all()
        )
        assert priya_chat == []
