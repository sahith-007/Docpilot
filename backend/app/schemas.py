from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    specialty: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    specialty: str = Field(default="General Medicine", max_length=120)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class ClinicalNoteRead(BaseModel):
    id: str
    case_id: str
    note_type: str
    author_role: str
    note_date: str
    title: str
    body: str

    model_config = {"from_attributes": True}


class ClinicalCaseRead(BaseModel):
    id: str
    patient_name: str
    mrn: str
    age: int
    sex: str
    primary_concern: str
    risk_level: str
    status: str
    admitted_at: str
    suggested_questions: list[str] = []

    model_config = {"from_attributes": True}


class TimelineEvent(BaseModel):
    date: str
    label: str
    detail: str


class MedicationRead(BaseModel):
    name: str
    dose: str
    status: str


class ClinicalMeasure(BaseModel):
    name: str
    value: str
    flag: str


class ClinicalCaseDetail(ClinicalCaseRead):
    notes: list[ClinicalNoteRead]
    timeline: list[TimelineEvent]
    active_problems: list[str]
    medications: list[MedicationRead]
    labs: list[ClinicalMeasure]
    vitals: list[ClinicalMeasure]


class EvidenceChunk(BaseModel):
    note_id: str
    case_id: str
    note_type: str
    note_date: str
    title: str
    chunk_id: str
    text: str
    score: float


class CitationRead(BaseModel):
    source_number: int
    note_id: str
    chunk_id: str
    title: str
    note_type: str
    note_date: str


class AskRequest(BaseModel):
    case_id: str
    question: str = Field(min_length=8, max_length=800)
    note_types: list[str] | None = None
    max_evidence: int = Field(default=5, ge=2, le=8)


class AskResponse(BaseModel):
    answer_id: str
    question_id: str
    answer: str
    confidence: str
    model: str
    provider_used: str
    created_at: datetime
    evidence: list[EvidenceChunk]
    citations: list[CitationRead]
    limits: list[str]


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    answer_id: str | None = None
    confidence: str | None = None
    model: str | None = None
    provider_used: str | None = None
    feedback_status: str | None = None
    feedback_message: str | None = None
    feedback_updated_at: datetime | None = None
    evidence: list[EvidenceChunk] = []
    citations: list[CitationRead] = []
    limits: list[str] = []


class ConversationResponse(BaseModel):
    case_id: str
    messages: list[ChatMessage]


class SummaryRequest(BaseModel):
    case_id: str


class SummaryResponse(BaseModel):
    case_id: str
    sections: dict[str, str]
    evidence: list[EvidenceChunk]


class DebugConfigResponse(BaseModel):
    demo_mode: bool
    model: str
    openai_key_present: bool


class FeedbackRequest(BaseModel):
    answer_id: str
    status: str | None = Field(default=None, pattern="^(accepted|review|rejected)$")
    verdict: str | None = Field(default=None, pattern="^(accepted|needs_review|rejected)$")
    reason: str | None = Field(
        default=None,
        pattern="^(grounded|missing_evidence|unsupported_claim|wrong_context|unclear)$",
    )
    notes: str = Field(default="", max_length=600)

    @model_validator(mode="after")
    def require_feedback_decision(self) -> "FeedbackRequest":
        if self.status is None and self.verdict is None:
            raise ValueError("Feedback status is required.")
        return self


class FeedbackResponse(BaseModel):
    id: str
    answer_id: str
    status: str
    verdict: str
    reason: str
    notes: str
    updated_at: datetime
    message: str


class BenchmarkItemResult(BaseModel):
    id: str
    case_id: str
    question: str
    accepted: bool
    score: int
    expected_evidence: list[str]
    matched_evidence: list[str]


class BenchmarkResponse(BaseModel):
    run_id: str
    label: str
    total: int
    accepted: int
    acceptance_rate: int
    improvement_from_baseline: int
    results: list[BenchmarkItemResult]
