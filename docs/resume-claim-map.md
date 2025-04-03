# Resume Claim Map

This file maps the resume bullets to concrete repo artifacts so the project can be defended in an interview.

## "Architected DocPilot as a full-stack AI clinical assistant..."

- FastAPI backend: `backend/app/main.py`
- React frontend: `frontend/src/App.tsx`
- Synthetic clinical data: `backend/app/data/synthetic_cases.json`
- Structured summaries: `POST /assistant/summary`
- Evidence review UI: source note panel in the React workspace
- Secure APIs: JWT auth dependency in `backend/app/core/security.py`

## "Benchmarked generated answers against curated examples..."

- Curated benchmark set: `backend/app/data/curated_eval_set.json`
- Benchmark service: `backend/app/services/evaluator.py`
- CLI benchmark runner: `evals/run_benchmark.py`
- Benchmark dashboard: frontend "Benchmarks" panel

The improvement percentage should be reported from an actual benchmark run. Do not hard-code `35%` unless the run produces that result.

## "Hardened authentication, request validation, Docker packaging..."

- Authentication: `POST /auth/login` and bearer-token dependencies
- Validation: Pydantic request models in `backend/app/schemas.py`
- Docker packaging: `docker-compose.yml`, backend and frontend Dockerfiles
- Structured logs: `backend/app/core/logging.py`
- Regression checks: backend tests and benchmark CLI

