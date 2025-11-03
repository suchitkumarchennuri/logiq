"""Celery tasks for asynchronous processing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict

from app.celery_app import celery
from app.db.models import LogRecord
from app.db.session import db_session_scope, init_db
from app.services.embeddings import get_embedding_service


logger = logging.getLogger(__name__)

_db_initialized = False
_db_lock = Lock()


def ensure_database_ready() -> None:
    """Idempotently create tables and required extensions."""

    global _db_initialized
    if _db_initialized:
        return

    with _db_lock:
        if _db_initialized:
            return
        init_db()
        _db_initialized = True


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            logger.warning(
                "Unable to parse log timestamp '%s'; defaulting to now", value)
            return datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return datetime.now(timezone.utc)


@celery.task(name="process_log", bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_log(self, payload: Dict[str, Any]) -> str:
    """Persist a log and generate its embedding."""

    ensure_database_ready()

    embedding_service = get_embedding_service()
    log_timestamp = _parse_timestamp(payload.get("log_timestamp"))
    attributes = payload.get("attributes") or {}

    record = LogRecord(
        service=payload["service"],
        level=payload["level"].upper(),
        message=payload["message"],
        log_timestamp=log_timestamp,
        attributes=attributes,
    )

    record.embedding = embedding_service.embed_text(record.message)

    with db_session_scope() as session:
        session.add(record)

    logger.info("Stored log %s for service=%s level=%s",
                record.id, record.service, record.level)
    return str(record.id)
