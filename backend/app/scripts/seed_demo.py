from app.db.session import Base, engine, ensure_runtime_schema, session_scope
from app.services.seed import seed_demo_data


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    with session_scope() as db:
        seed_demo_data(db)
    print("Seeded synthetic demo doctors, patients, notes, assignments, and cleared chat history.")


if __name__ == "__main__":
    main()
