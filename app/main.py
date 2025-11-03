"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.db.session import init_db


settings = get_settings()

logging.basicConfig(level=getattr(
    logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure database schema is ready."""

    init_db()


@app.get("/healthz")
async def health_check() -> dict:
    """Lightweight readiness ping."""

    return {"status": "ok"}


app.include_router(api_router)
