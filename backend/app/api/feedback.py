from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import ClinicalAnswer, ReviewerFeedback, User
from app.db.session import get_db
from app.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    answer = db.get(ClinicalAnswer, payload.answer_id)
    if answer is None or answer.question.user_id != user.id:
        raise HTTPException(status_code=404, detail="Answer not found")
    feedback = ReviewerFeedback(
        answer_id=payload.answer_id,
        reviewer_id=user.id,
        verdict=payload.verdict,
        reason=payload.reason,
        notes=payload.notes,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
