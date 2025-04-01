from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import BenchmarkResponse
from app.services.evaluator import run_benchmark

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("/run", response_model=BenchmarkResponse)
def run_regression_benchmark(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    response = run_benchmark(db)
    db.commit()
    return response

