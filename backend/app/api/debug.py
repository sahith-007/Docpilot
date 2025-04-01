from fastapi import APIRouter

from app.core.config import settings
from app.schemas import DebugConfigResponse

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/config", response_model=DebugConfigResponse)
def debug_config() -> DebugConfigResponse:
    return DebugConfigResponse(
        demo_mode=settings.demo_mode,
        model=settings.openai_chat_model,
        openai_key_present=bool(settings.openai_api_key),
    )
