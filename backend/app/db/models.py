from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(80), default="physician")
    specialty: Mapped[str] = mapped_column(String(120), default="General Medicine")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignments: Mapped[list["PatientAssignment"]] = relationship(back_populates="doctor")


class ClinicalCase(Base):
    __tablename__ = "clinical_cases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    patient_name: Mapped[str] = mapped_column(String(160))
    mrn: Mapped[str] = mapped_column(String(40), unique=True)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(40))
    primary_concern: Mapped[str] = mapped_column(String(255))
    risk_level: Mapped[str] = mapped_column(String(40), default="watch")
    status: Mapped[str] = mapped_column(String(80), default="active")
    admitted_at: Mapped[str] = mapped_column(String(40))
    timeline_json: Mapped[str] = mapped_column(Text, default="[]")
    active_problems_json: Mapped[str] = mapped_column(Text, default="[]")
    medications_json: Mapped[str] = mapped_column(Text, default="[]")
    labs_json: Mapped[str] = mapped_column(Text, default="[]")
    vitals_json: Mapped[str] = mapped_column(Text, default="[]")
    suggested_questions_json: Mapped[str] = mapped_column(Text, default="[]")

    notes: Mapped[list["ClinicalNote"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="ClinicalNote.note_date",
    )
    questions: Mapped[list["ClinicalQuestion"]] = relationship(back_populates="case")
    assignments: Mapped[list["PatientAssignment"]] = relationship(back_populates="case")


class PatientAssignment(Base):
    __tablename__ = "patient_assignments"
    __table_args__ = (UniqueConstraint("doctor_id", "case_id", name="uq_doctor_case"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    doctor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    doctor: Mapped[User] = relationship(back_populates="assignments")
    case: Mapped[ClinicalCase] = relationship(back_populates="assignments")


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True)
    note_type: Mapped[str] = mapped_column(String(80), index=True)
    author_role: Mapped[str] = mapped_column(String(80))
    note_date: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)

    case: Mapped[ClinicalCase] = relationship(back_populates="notes")


class ClinicalQuestion(Base):
    __tablename__ = "clinical_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    case: Mapped[ClinicalCase] = relationship(back_populates="questions")
    answer: Mapped["ClinicalAnswer"] = relationship(back_populates="question", uselist=False)


class ClinicalAnswer(Base):
    __tablename__ = "clinical_answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    question_id: Mapped[str] = mapped_column(ForeignKey("clinical_questions.id"), index=True)
    answer_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(40))
    evidence_json: Mapped[str] = mapped_column(Text)
    limits_json: Mapped[str] = mapped_column(Text, default="[]")
    model_name: Mapped[str] = mapped_column(String(80), default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped[ClinicalQuestion] = relationship(back_populates="answer")
    feedback_items: Mapped[list["ReviewerFeedback"]] = relationship(back_populates="answer")


class ReviewerFeedback(Base):
    __tablename__ = "reviewer_feedback"
    __table_args__ = (UniqueConstraint("answer_id", "reviewer_id", name="uq_answer_reviewer_feedback"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    answer_id: Mapped[str] = mapped_column(ForeignKey("clinical_answers.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    answer: Mapped[ClinicalAnswer] = relationship(back_populates="feedback_items")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    label: Mapped[str] = mapped_column(String(120))
    total: Mapped[int] = mapped_column(Integer)
    accepted: Mapped[int] = mapped_column(Integer)
    acceptance_rate: Mapped[int] = mapped_column(Integer)
    details_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
