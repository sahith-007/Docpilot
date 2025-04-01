import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import BenchmarkRun
from app.schemas import BenchmarkItemResult, BenchmarkResponse
from app.services.retrieval import search_evidence

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BASELINE_ACCEPTANCE_RATE = 51


def run_benchmark(db: Session, label: str = "retrieval-filtered-demo") -> BenchmarkResponse:
    payload = json.loads((DATA_DIR / "curated_eval_set.json").read_text())
    results: list[BenchmarkItemResult] = []

    for item in payload["items"]:
        evidence = search_evidence(
            case_id=item["case_id"],
            question=item["question"],
            note_types=item.get("note_types"),
            limit=5,
        )
        matched_ids = [chunk.note_id for chunk in evidence]
        expected_ids = item["expected_evidence"]
        matched_expected = [note_id for note_id in expected_ids if note_id in matched_ids]
        score = round((len(matched_expected) / max(len(expected_ids), 1)) * 100)
        accepted = score >= item.get("acceptance_threshold", 67)
        results.append(
            BenchmarkItemResult(
                id=item["id"],
                case_id=item["case_id"],
                question=item["question"],
                accepted=accepted,
                score=score,
                expected_evidence=expected_ids,
                matched_evidence=matched_ids,
            )
        )

    accepted_count = sum(1 for result in results if result.accepted)
    total = len(results)
    acceptance_rate = round((accepted_count / max(total, 1)) * 100)
    run = BenchmarkRun(
        label=label,
        total=total,
        accepted=accepted_count,
        acceptance_rate=acceptance_rate,
        details_json=json.dumps([result.model_dump() for result in results]),
    )
    db.add(run)
    db.flush()
    return BenchmarkResponse(
        run_id=run.id,
        label=label,
        total=total,
        accepted=accepted_count,
        acceptance_rate=acceptance_rate,
        improvement_from_baseline=max(0, acceptance_rate - BASELINE_ACCEPTANCE_RATE),
        results=results,
    )

