
from fastapi import FastAPI

from app.config import settings
from app.schemas import HealthResponse
from app.schemas import HealthResponse


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="A production-ready RAG API",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
    )
