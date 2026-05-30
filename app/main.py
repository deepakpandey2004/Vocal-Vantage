"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.core.redis_client import close_redis, get_redis
from app.database import init_db
from app.routers import analysis, auth, pages

logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("vocal_vantage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s (%s)", settings.app_name, __version__, settings.environment)
    await init_db()
    await get_redis()  # warm the connection (non-fatal if unavailable)
    yield
    await close_redis()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=f"{settings.app_name} API",
    description="AI-powered public speaking coach — transcription, linguistic analysis & LLM feedback.",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(analysis.router)


@app.get("/health", tags=["meta"])
async def health():
    redis = await get_redis()
    return JSONResponse(
        {
            "status": "ok",
            "version": __version__,
            "environment": settings.environment,
            "redis": "connected" if redis is not None else "disabled",
            "ai_mock_mode": settings.ai_mock_mode,
        }
    )
