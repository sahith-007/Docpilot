import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.schemas import EvidenceChunk


class OpenAIGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AnswerDraft:
    answer: str
    confidence: str
    limits: list[str]


SYSTEM_PROMPT = """You are DocPilot, a clinical assistant for synthetic healthcare notes.
Answer only from the supplied evidence and conversation context.
Do not add facts that are not in the evidence.
If evidence is insufficient, say what is missing.
Return only JSON with keys: answer, confidence, limits.
confidence must be one of: high, medium, low.
limits must be an array of short strings."""


def generate_openai_answer(
    question: str,
    evidence: list[EvidenceChunk],
    history: list[tuple[str, str]],
) -> AnswerDraft:
    if not settings.openai_api_key:
        raise OpenAIGenerationError("OpenAI API key is not configured.")

    payload = {
        "model": settings.openai_chat_model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _compose_user_prompt(question, evidence, history)},
        ],
        "max_output_tokens": 900,
    }
    try:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=35,
        )
    except httpx.HTTPError as exc:
        raise OpenAIGenerationError("OpenAI request failed before a response was returned.") from exc

    if response.status_code >= 400:
        raise OpenAIGenerationError(_api_error_message(response))

    return parse_answer_text(extract_response_text(response.json()))


def extract_response_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                return str(content["text"])

    raise OpenAIGenerationError("OpenAI response did not include text output.")


def parse_answer_text(text: str) -> AnswerDraft:
    cleaned = _strip_code_fence(text.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return AnswerDraft(
            answer=text.strip(),
            confidence="medium",
            limits=["Model returned unstructured text; verify citations manually."],
        )

    answer = str(parsed.get("answer", "")).strip()
    if not answer:
        raise OpenAIGenerationError("OpenAI response JSON did not include an answer.")

    confidence = str(parsed.get("confidence", "medium")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    raw_limits = parsed.get("limits", [])
    limits = [str(item).strip() for item in raw_limits if str(item).strip()] if isinstance(raw_limits, list) else []
    return AnswerDraft(answer=answer, confidence=confidence, limits=limits)


def _compose_user_prompt(
    question: str,
    evidence: list[EvidenceChunk],
    history: list[tuple[str, str]],
) -> str:
    history_block = "\n\n".join(
        f"Previous question: {previous_question}\nPrevious answer: {previous_answer}"
        for previous_question, previous_answer in history
    )
    evidence_block = "\n\n".join(
        f"[{idx + 1}] note_id={chunk.note_id} chunk_id={chunk.chunk_id} "
        f"title={chunk.title} date={chunk.note_date} type={chunk.note_type}\n{chunk.text}"
        for idx, chunk in enumerate(evidence)
    )
    return (
        f"Conversation context:\n{history_block or 'No prior case conversation.'}\n\n"
        f"Retrieved evidence:\n{evidence_block or 'No retrieved evidence.'}\n\n"
        f"Current question:\n{question}\n\n"
        "Write a concise clinical answer with bracketed evidence references like [1] when supported."
    )


def _api_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return f"OpenAI request failed with status {response.status_code}."

    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return f"OpenAI request failed: {error['message']}"
    return f"OpenAI request failed with status {response.status_code}."


def _strip_code_fence(text: str) -> str:
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text

