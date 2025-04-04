import json
import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import ClinicalAnswer, ClinicalCase, ClinicalQuestion
from app.schemas import (
    AskRequest,
    AskResponse,
    ChatMessage,
    CitationRead,
    ConversationResponse,
    EvidenceChunk,
    SummaryResponse,
)
from app.services.openai_client import AnswerDraft, generate_openai_answer
from app.services.feedback import latest_feedback_for_answer, message_for_status, status_from_verdict
from app.services.retrieval import search_evidence

logger = get_logger(__name__)


def answer_question(db: Session, user_id: str, request: AskRequest) -> AskResponse:
    clinical_case = db.get(ClinicalCase, request.case_id)
    if clinical_case is None:
        raise ValueError("Case not found")

    provider_used = _provider_used()
    active_model = _active_model_name()
    logger.info(
        "assistant_request_started",
        demo_mode=settings.demo_mode,
        model=settings.openai_chat_model,
        openai_key_present=bool(settings.openai_api_key),
        case_id=request.case_id,
        question_preview=_question_preview(request.question),
        provider_used=provider_used,
    )

    evidence = search_evidence(
        case_id=request.case_id,
        question=request.question,
        note_types=request.note_types,
        limit=request.max_evidence,
    )
    history = _conversation_context(db, user_id, request.case_id)
    answer_draft = _generate_answer(request.question, evidence, history)

    question = ClinicalQuestion(
        case_id=request.case_id,
        user_id=user_id,
        question=request.question,
    )
    db.add(question)
    db.flush()

    answer = ClinicalAnswer(
        question_id=question.id,
        answer_text=answer_draft.answer,
        confidence=answer_draft.confidence,
        evidence_json=json.dumps([chunk.model_dump() for chunk in evidence]),
        limits_json=json.dumps(answer_draft.limits),
        model_name=active_model,
    )
    db.add(answer)
    db.flush()
    db.refresh(question)
    db.refresh(answer)

    logger.info(
        "assistant_answer_created",
        case_id=request.case_id,
        question_id=question.id,
        confidence=answer_draft.confidence,
        evidence_count=len(evidence),
        model=active_model,
        provider_used=provider_used,
    )

    return AskResponse(
        answer_id=answer.id,
        question_id=question.id,
        answer=answer.answer_text,
        confidence=answer.confidence,
        model=answer.model_name,
        provider_used=provider_used,
        created_at=answer.created_at,
        evidence=evidence,
        citations=_citations_from_evidence(evidence),
        limits=answer_draft.limits,
    )


def summarize_case(db: Session, case_id: str) -> SummaryResponse:
    clinical_case = db.get(ClinicalCase, case_id)
    if clinical_case is None:
        raise ValueError("Case not found")

    evidence = search_evidence(
        case_id=case_id,
        question="active problems medications labs imaging disposition risks",
        limit=8,
    )
    sections = _build_structured_summary(clinical_case, evidence)
    return SummaryResponse(case_id=case_id, sections=sections, evidence=evidence[:5])


def conversation_for_case(db: Session, user_id: str, case_id: str) -> ConversationResponse:
    clinical_case = db.get(ClinicalCase, case_id)
    if clinical_case is None:
        raise ValueError("Case not found")

    questions = (
        db.query(ClinicalQuestion)
        .filter(ClinicalQuestion.case_id == case_id, ClinicalQuestion.user_id == user_id)
        .order_by(ClinicalQuestion.created_at.asc(), ClinicalQuestion.id.asc())
        .all()
    )
    messages: list[ChatMessage] = []
    for question in questions:
        messages.append(
            ChatMessage(
                id=question.id,
                role="user",
                content=question.question,
                created_at=question.created_at,
            )
        )
        if question.answer:
            evidence = _evidence_from_json(question.answer.evidence_json)
            feedback = latest_feedback_for_answer(db, user_id, question.answer.id)
            feedback_status = status_from_verdict(feedback.verdict) if feedback else None
            messages.append(
                ChatMessage(
                    id=question.answer.id,
                    role="assistant",
                    content=question.answer.answer_text,
                    created_at=question.answer.created_at,
                    answer_id=question.answer.id,
                    confidence=question.answer.confidence,
                    model=question.answer.model_name,
                    provider_used=_provider_from_model(question.answer.model_name),
                    feedback_status=feedback_status,
                    feedback_message=message_for_status(feedback_status) if feedback_status else None,
                    feedback_updated_at=feedback.updated_at if feedback else None,
                    evidence=evidence,
                    citations=_citations_from_evidence(evidence),
                    limits=_limits_from_json(question.answer.limits_json),
                )
            )
    return ConversationResponse(case_id=case_id, messages=messages)


def _generate_answer(
    question: str,
    evidence: list[EvidenceChunk],
    history: list[tuple[str, str]],
) -> AnswerDraft:
    if settings.demo_mode:
        if not evidence:
            return AnswerDraft(
                answer=(
                    "The retrieved notes for this selected patient do not provide enough evidence "
                    "to answer that safely."
                ),
                confidence="low",
                limits=["No supporting evidence was retrieved for this case."],
            )
        answer, confidence, limits = _generate_demo_answer(question, evidence)
        return AnswerDraft(answer=answer, confidence=confidence, limits=limits)
    return generate_openai_answer(question, evidence, history)


def _conversation_context(db: Session, user_id: str, case_id: str) -> list[tuple[str, str]]:
    questions = (
        db.query(ClinicalQuestion)
        .filter(ClinicalQuestion.case_id == case_id, ClinicalQuestion.user_id == user_id)
        .order_by(ClinicalQuestion.created_at.desc(), ClinicalQuestion.id.desc())
        .limit(4)
        .all()
    )
    pairs = [
        (question.question, question.answer.answer_text)
        for question in reversed(questions)
        if question.answer is not None
    ]
    return pairs


def _generate_demo_answer(question: str, evidence: list[EvidenceChunk]) -> tuple[str, str, list[str]]:
    if not evidence:
        return (
            "I do not have enough retrieved evidence in this case to answer that safely.",
            "low",
            ["No matching source notes were retrieved."],
        )

    top = evidence[:3]
    signal_terms = _clinical_terms(question)
    support_lines = []
    for chunk in top:
        sentence = _best_sentence(chunk.text, signal_terms)
        support_lines.append(f"{sentence} [{chunk.note_id}]")

    answer = " ".join(support_lines)
    if len(top) > 1:
        answer += " Taken together, the cited notes support a grounded, case-specific answer rather than a general clinical guess."

    confidence = "high" if len(evidence) >= 3 and evidence[0].score >= 0.75 else "medium"
    limits = []
    if confidence != "high":
        limits.append("The answer is based on a narrow evidence set and should be reviewed.")
    return answer, confidence, limits


def _build_structured_summary(
    clinical_case: ClinicalCase,
    evidence: list[EvidenceChunk],
) -> dict[str, str]:
    active_problems = _json_list(clinical_case.active_problems_json)
    medications = _json_list(clinical_case.medications_json)
    labs = _json_list(clinical_case.labs_json)
    vitals = _json_list(clinical_case.vitals_json)
    evidence_sentence = _first_evidence_sentence(evidence)

    return {
        "Snapshot": f"{clinical_case.age}-year-old {clinical_case.sex} admitted for {clinical_case.primary_concern}.",
        "Active Problems": "; ".join(str(item) for item in active_problems[:5])
        or "Active problems are pending source-note review.",
        "Pertinent Evidence": _clinical_measure_summary(labs + vitals)
        or evidence_sentence
        or "No strong signal found in retrieved notes.",
        "Medications And Plan": _medication_summary(medications)
        or "Medication plan is pending source-note review.",
        "Review Flags": "Verify against source notes before using this outside the synthetic demo.",
    }


def _clinical_terms(text: str) -> set[str]:
    stop_words = {
        "what",
        "which",
        "does",
        "with",
        "from",
        "that",
        "this",
        "main",
        "driver",
        "evidence",
        "supports",
        "support",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
        if token not in stop_words
    }


def _best_sentence(text: str, terms: set[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return text[:280]
    ranked = sorted(
        sentences,
        key=lambda sentence: sum(1 for term in terms if term in sentence.lower()),
        reverse=True,
    )
    return ranked[0][:320]


def _extract_summary_line(text: str, terms: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    matches = [
        sentence.strip()
        for sentence in sentences
        if any(term in sentence.lower() for term in terms)
    ]
    if not matches:
        return "No strong signal found in retrieved notes."
    return " ".join(matches[:2])[:420]


def _citations_from_evidence(evidence: list[EvidenceChunk]) -> list[CitationRead]:
    return [
        CitationRead(
            source_number=idx + 1,
            note_id=chunk.note_id,
            chunk_id=chunk.chunk_id,
            title=chunk.title,
            note_type=chunk.note_type,
            note_date=chunk.note_date,
        )
        for idx, chunk in enumerate(evidence)
    ]


def _evidence_from_json(raw: str) -> list[EvidenceChunk]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [EvidenceChunk.model_validate(item) for item in payload]


def _limits_from_json(raw: str) -> list[str]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if str(item).strip()]


def _json_list(raw: str) -> list:
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def _clinical_measure_summary(items: list) -> str:
    parts = []
    for item in items[:6]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        value = str(item.get("value", "")).strip()
        flag = str(item.get("flag", "")).strip()
        if name and value:
            parts.append(f"{name}: {value}" + (f" ({flag})" if flag else ""))
    return "; ".join(parts)


def _medication_summary(items: list) -> str:
    parts = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        dose = str(item.get("dose", "")).strip()
        status = str(item.get("status", "")).strip()
        if name:
            parts.append(f"{name} {dose}".strip() + (f" - {status}" if status else ""))
    return "; ".join(parts)


def _first_evidence_sentence(evidence: list[EvidenceChunk]) -> str:
    if not evidence:
        return ""
    return _best_sentence(evidence[0].text, set())[:420]


def _active_model_name() -> str:
    return "demo-local" if settings.demo_mode else settings.openai_chat_model


def _provider_used() -> str:
    return "demo" if settings.demo_mode else "openai"


def _provider_from_model(model_name: str | None) -> str | None:
    if not model_name:
        return None
    if model_name == "demo-local":
        return "demo"
    if model_name.startswith("gpt-") or model_name.startswith("o"):
        return "openai"
    return "unknown"


def _question_preview(question: str) -> str:
    return question.strip().replace("\n", " ")[:120]
