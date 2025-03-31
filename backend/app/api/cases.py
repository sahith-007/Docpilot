import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_current_user
from app.db.models import ClinicalCase, PatientAssignment, User
from app.db.session import get_db
from app.schemas import ClinicalCaseDetail, ClinicalCaseRead

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[ClinicalCaseRead])
def list_cases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClinicalCaseRead]:
    cases = (
        db.query(ClinicalCase)
        .join(PatientAssignment, PatientAssignment.case_id == ClinicalCase.id)
        .filter(PatientAssignment.doctor_id == user.id)
        .order_by(ClinicalCase.admitted_at.desc())
        .all()
    )
    return [_case_read(case) for case in cases]


@router.get("/{case_id}", response_model=ClinicalCaseDetail)
def get_case(
    case_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicalCaseDetail:
    clinical_case = (
        db.query(ClinicalCase)
        .join(PatientAssignment, PatientAssignment.case_id == ClinicalCase.id)
        .options(selectinload(ClinicalCase.notes))
        .filter(ClinicalCase.id == case_id, PatientAssignment.doctor_id == user.id)
        .first()
    )
    if clinical_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_detail(clinical_case)


def user_can_access_case(db: Session, user_id: str, case_id: str) -> bool:
    return (
        db.query(PatientAssignment)
        .filter(PatientAssignment.doctor_id == user_id, PatientAssignment.case_id == case_id)
        .first()
        is not None
    )


def _load_json(raw: str, fallback):
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _case_read(case: ClinicalCase) -> ClinicalCaseRead:
    return ClinicalCaseRead(
        id=case.id,
        patient_name=case.patient_name,
        mrn=case.mrn,
        age=case.age,
        sex=case.sex,
        primary_concern=case.primary_concern,
        risk_level=case.risk_level,
        status=case.status,
        admitted_at=case.admitted_at,
        suggested_questions=_load_json(case.suggested_questions_json, []),
    )


def _case_detail(case: ClinicalCase) -> ClinicalCaseDetail:
    return ClinicalCaseDetail(
        **_case_read(case).model_dump(),
        notes=case.notes,
        timeline=_load_json(case.timeline_json, []),
        active_problems=_load_json(case.active_problems_json, []),
        medications=_load_json(case.medications_json, []),
        labs=_load_json(case.labs_json, []),
        vitals=_load_json(case.vitals_json, []),
    )
