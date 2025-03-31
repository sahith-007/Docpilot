from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import assistant, auth, benchmarks, cases, debug, feedback
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import Base, engine, ensure_runtime_schema, session_scope
from app.services.retrieval import rebuild_index
from app.services.seed import seed_demo_data

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="DocPilot API",
    version="0.1.0",
    description="Synthetic clinical assistant API with retrieval, evidence, and benchmark workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(assistant.router)
app.include_router(feedback.router)
app.include_router(benchmarks.router)
app.include_router(debug.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    with session_scope() as db:
        seed_demo_data(db)
        rebuild_index(db)
    logger.info(
        "docpilot_started",
        demo_mode=settings.demo_mode,
        model=settings.openai_chat_model,
        openai_key_present=bool(settings.openai_api_key),
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "docpilot-api"}
