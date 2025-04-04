from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "specialty" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN specialty VARCHAR(120) DEFAULT 'General Medicine'")
                )

    if "clinical_cases" in table_names:
        case_columns = {column["name"] for column in inspector.get_columns("clinical_cases")}
        case_json_columns = {
            "timeline_json": "[]",
            "active_problems_json": "[]",
            "medications_json": "[]",
            "labs_json": "[]",
            "vitals_json": "[]",
            "suggested_questions_json": "[]",
        }
        with engine.begin() as connection:
            for column_name, default_value in case_json_columns.items():
                if column_name not in case_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE clinical_cases ADD COLUMN {column_name} "
                            f"TEXT DEFAULT '{default_value}'"
                        )
                    )

    if "clinical_answers" not in inspector.get_table_names():
        return

    answer_columns = {column["name"] for column in inspector.get_columns("clinical_answers")}
    if "model_name" not in answer_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE clinical_answers "
                    "ADD COLUMN model_name VARCHAR(80) DEFAULT 'unknown'"
                )
            )
    if "limits_json" not in answer_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE clinical_answers ADD COLUMN limits_json TEXT DEFAULT '[]'")
            )

    if "reviewer_feedback" in table_names:
        feedback_columns = {column["name"] for column in inspector.get_columns("reviewer_feedback")}
        if "updated_at" not in feedback_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE reviewer_feedback ADD COLUMN updated_at DATETIME")
                )
