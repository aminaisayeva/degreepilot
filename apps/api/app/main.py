from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.db import init_db
from app.seed.demo_student import ensure_demo_student
from app.seed.runner import seed_all

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_startup:
        seed_all()
        ensure_demo_student()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "DegreePilot — agentic academic planning. "
        "LLMs explain and interact; the planning engine validates."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/courses",
            "/courses/{code}",
            "/requirements",
            "/requirements/{program}",
            "/students",
            "/students/{id}/audit",
            "/plans/generate",
            "/plans/validate",
            "/plans/compare",
            "/advisor/chat",
            "/advisor/v2/chat",
            "/admin/sync",
            "/admin/sync/status",
            "/admin/accuracy",
            "/admin/accuracy/data",
            "/admin/accuracy/check",
        ],
    }
