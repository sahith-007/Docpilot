# DocPilot

DocPilot is a full-stack AI clinical assistant prototype built around synthetic patient notes. It gives a doctor a focused workspace for reviewing case context, asking evidence-grounded questions, checking cited source notes, and tracking reviewer feedback against a curated benchmark set.

The project is intentionally scoped for a portfolio/demo setting: all clinical content is synthetic, the app can run without an OpenAI key in deterministic demo mode, and the code keeps the retrieval and evaluation pieces visible instead of hiding them behind a black box.

## Stack

- FastAPI backend with typed request/response schemas
- React + Vite frontend
- OpenAI Responses API for chat answers
- ChromaDB vector store for clinical-note retrieval
- PostgreSQL for users, cases, notes, questions, and feedback
- Docker Compose for local services

## What It Demonstrates

- Retrieval workflows over synthetic clinical notes
- Structured clinical summaries with cited evidence
- Evidence review screens for source note inspection
- Confidence states for grounded responses
- Reviewer feedback loops and benchmark reporting
- Auth, request validation, structured logs, and regression checks

## Quick Start

Copy the environment template for the backend:

```bash
cp .env.example backend/.env
```

Run the stack:

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs

Demo credentials:

```text
Dr. Maya Chen      maya.chen@docpilot.health  / demo-clinical
Dr. Sahith Reddy   sahith@docpilot.health     / demo-clinical
Dr. Vijay Rao      vijay@docpilot.health      / demo-clinical
Dr. Ashish Patel   ashish@docpilot.health     / demo-clinical
```

The backend runs in deterministic demo mode when `DEMO_MODE=true`. Add a key in `backend/.env`, set `DEMO_MODE=false`, and use `OPENAI_CHAT_MODEL=gpt-4.1-mini` for OpenAI-backed generation.

## Demo Data

The backend seeds synthetic doctors, assigned patients, clinical notes, timeline entries, medications, labs, vitals, and suggested questions on startup. Seeding is idempotent, so restarting the backend refreshes the demo dataset without duplicating cases.

Startup also clears saved chat questions, answers, and feedback so stale demo-local answers do not appear in a fresh presentation run. To clear only chat history without resetting patient data:

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.reset_chat
```

To seed the synthetic doctors and patients without starting the API server:

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.seed_demo
```

To confirm real OpenAI mode is active without exposing secrets:

```bash
curl http://localhost:8000/debug/config
```

For a clean local SQLite reset during development, stop the backend, remove `backend/docpilot.db`, then start the backend again. For Docker/PostgreSQL, reset the local database volume with:

```bash
docker compose down -v
docker compose up --build
```

All seeded clinical content is synthetic and intended only for product demos.

## Local Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Run the benchmark:

```bash
python evals/run_benchmark.py --base-url http://localhost:8000
```

## Safety Note

DocPilot is a prototype for synthetic healthcare workflows only. It is not a medical device, does not process real patient data, and should not be used for clinical decision-making.
