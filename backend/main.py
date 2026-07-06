from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from config.settings import settings
from database.connection import initialize_database
from database import repositories as repo


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/health")
def health() -> dict:
    initialize_database()
    table_count = repo.row("SELECT count(*) AS n FROM sqlite_master WHERE type='table'")["n"]
    model_rows = repo.rows("SELECT name, availability, fallback_state FROM model_registry ORDER BY name")
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": {"path": str(settings.database_path), "tables": table_count, "status": "ok"},
        "models": model_rows,
        "timezone": settings.timezone,
    }
