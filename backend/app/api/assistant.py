from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.api.cases import user_can_access_case
from app.schemas import AskRequest, AskResponse, ConversationResponse, SummaryRequest, SummaryResponse
from app.services.assistant import answer_question, conversation_for_case, summarize_case
from app.services.openai_client import OpenAIGenerationError

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/ask", response_model=AskResponse)
def ask_docpilot(
    payload: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    if not user_can_access_case(db, user.id, payload.case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        response = answer_question(db, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpenAIGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail={"type": "openai_error", "message": str(exc)},
        ) from exc
    db.commit()
    return response


@router.post("/summary", response_model=SummaryResponse)
def case_summary(
    payload: SummaryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    if not user_can_access_case(db, user.id, payload.case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        return summarize_case(db, payload.case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations/{case_id}", response_model=ConversationResponse)
def case_conversation(
    case_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    if not user_can_access_case(db, user.id, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        return conversation_for_case(db, user.id, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
