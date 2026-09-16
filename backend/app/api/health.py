from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.providers.search.factory import build_search_registry
from app.database.mongodb import get_database
from app.database.qdrant import VectorStore

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


@router.get("", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="healthy", service=settings.app_name, environment=settings.environment)


@router.get("/ready")
async def readiness(response: Response, settings: Settings = Depends(get_settings)) -> dict:
    checks = {"mongodb": "healthy", "qdrant": "healthy"}
    try:
        await get_database().command("ping")
    except Exception:
        checks["mongodb"] = "offline"
    try:
        await VectorStore(settings).client.get_collections()
    except Exception:
        checks["qdrant"] = "offline"
    ready = all(value == "healthy" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "not_ready", "checks": checks}


@router.get("/providers")
async def provider_health(settings: Settings = Depends(get_settings)) -> dict:
    providers = {
        "gemini": bool(settings.gemini_api_key),
        "groq": bool(settings.groq_api_key),
        "mistral": bool(settings.mistral_api_key),
        "openrouter": bool(settings.openrouter_api_key),
    }
    return {"llm_providers": [{"name": name, "enabled": enabled, "health": "healthy" if enabled else "misconfigured"} for name, enabled in providers.items()], "search_providers": build_search_registry(settings).status()}
