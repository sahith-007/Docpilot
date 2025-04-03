# Architecture

DocPilot is designed as a small clinical workspace with visible retrieval, evidence, and evaluation surfaces.

## Runtime Flow

1. Synthetic notes are seeded into PostgreSQL.
2. Each note is chunked into clinically meaningful passages.
3. Chunks are embedded and indexed in ChromaDB.
4. A doctor asks a case-specific question from the React UI.
5. FastAPI validates the request, checks auth, and calls the retrieval service.
6. LangChain assembles a constrained prompt with the retrieved evidence.
7. The answer returns with confidence, cited evidence chunks, and a safety note when evidence is thin.
8. Reviewer feedback is stored in PostgreSQL and appears in the benchmark dashboard.

## Backend Modules

- `app.api`: HTTP routes and dependency wiring
- `app.core`: settings, auth helpers, and logging
- `app.db`: SQLAlchemy models and sessions
- `app.services.retrieval`: note chunking, metadata filters, and vector search
- `app.services.assistant`: prompt construction, OpenAI/LangChain generation, and demo fallback
- `app.services.evaluator`: curated benchmark scoring and regression checks

## Data Stores

PostgreSQL stores durable application records: users, cases, notes, questions, answers, feedback, and benchmark runs.

ChromaDB stores embedded note chunks with metadata such as case ID, note type, author role, and note date. This makes the retrieval filters inspectable and easy to explain during a demo.

## Demo Mode

When `OPENAI_API_KEY` is empty or `DEMO_MODE=true`, DocPilot uses deterministic extraction over retrieved evidence. That keeps the app demoable without external API access while preserving the same request and response shape.

