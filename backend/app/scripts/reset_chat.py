from app.db.session import Base, engine, ensure_runtime_schema, session_scope
from app.services.seed import reset_chat_history


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    with session_scope() as db:
        counts = reset_chat_history(db)
    print(
        "Cleared chat history: "
        f"{counts['questions']} question(s), "
        f"{counts['answers']} answer(s), "
        f"{counts['feedback']} feedback item(s)."
    )


if __name__ == "__main__":
    main()
