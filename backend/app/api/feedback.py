from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.cases import user_can_access_case
from app.core.security import get_current_user
from app.db.models import ClinicalAnswer, User
from app.db.session import get_db
from app.schemas import FeedbackRequest, FeedbackResponse
from app.services.feedback import upsert_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    answer = db.get(ClinicalAnswer, payload.answer_id)
    if (
        answer is None
        or answer.question.user_id != user.id
        or not user_can_access_case(db, user.id, answer.question.case_id)
    ):
        raise HTTPException(status_code=404, detail="Answer not found")
    try:
        return upsert_feedback(db, user, answer, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
