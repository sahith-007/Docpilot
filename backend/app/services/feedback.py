from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import ClinicalAnswer, ReviewerFeedback, User
from app.schemas import FeedbackRequest, FeedbackResponse

STATUS_TO_VERDICT = {
    "accepted": "accepted",
    "review": "needs_review",
    "rejected": "rejected",
}
VERDICT_TO_STATUS = {verdict: status for status, verdict in STATUS_TO_VERDICT.items()}
DEFAULT_REASON = {
    "accepted": "grounded",
    "review": "missing_evidence",
    "rejected": "unsupported_claim",
}
FEEDBACK_MESSAGES = {
    "accepted": "Accepted saved",
    "review": "Review saved",
    "rejected": "Rejected saved",
}


def upsert_feedback(
    db: Session,
    user: User,
    answer: ClinicalAnswer,
    payload: FeedbackRequest,
) -> FeedbackResponse:
    status = normalize_status(payload.status, payload.verdict)
    verdict = STATUS_TO_VERDICT[status]
    reason = payload.reason or DEFAULT_REASON[status]

    existing_items = (
        db.query(ReviewerFeedback)
        .filter(
            ReviewerFeedback.answer_id == answer.id,
            ReviewerFeedback.reviewer_id == user.id,
        )
        .all()
    )
    feedback = _latest_from_items(existing_items)
    if feedback is None:
        feedback = ReviewerFeedback(answer_id=answer.id, reviewer_id=user.id)
        db.add(feedback)

    for duplicate in existing_items:
        if feedback is not None and duplicate.id != feedback.id:
            db.delete(duplicate)

    feedback.verdict = verdict
    feedback.reason = reason
    feedback.notes = payload.notes
    feedback.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(feedback)
    return response_from_feedback(feedback)


def latest_feedback_for_answer(
    db: Session,
    user_id: str,
    answer_id: str,
) -> ReviewerFeedback | None:
    items = (
        db.query(ReviewerFeedback)
        .filter(
            ReviewerFeedback.answer_id == answer_id,
            ReviewerFeedback.reviewer_id == user_id,
        )
        .all()
    )
    return _latest_from_items(items)


def response_from_feedback(feedback: ReviewerFeedback) -> FeedbackResponse:
    status = status_from_verdict(feedback.verdict)
    return FeedbackResponse(
        id=feedback.id,
        answer_id=feedback.answer_id,
        status=status,
        verdict=feedback.verdict,
        reason=feedback.reason,
        notes=feedback.notes,
        updated_at=feedback.updated_at or feedback.created_at,
        message=FEEDBACK_MESSAGES[status],
    )


def normalize_status(status: str | None, verdict: str | None) -> str:
    if status:
        return status
    if verdict and verdict in VERDICT_TO_STATUS:
        return VERDICT_TO_STATUS[verdict]
    raise ValueError("Feedback status is required.")


def status_from_verdict(verdict: str) -> str:
    return VERDICT_TO_STATUS.get(verdict, "review")


def message_for_status(status: str) -> str:
    return FEEDBACK_MESSAGES.get(status, "Feedback saved")


def _latest_from_items(items: list[ReviewerFeedback]) -> ReviewerFeedback | None:
    if not items:
        return None
    return max(
        items,
        key=lambda item: (
            _datetime_key(item.updated_at or item.created_at),
            _datetime_key(item.created_at),
            item.id,
        ),
    )


def _datetime_key(value: datetime | None) -> str:
    return value.isoformat() if value else ""
