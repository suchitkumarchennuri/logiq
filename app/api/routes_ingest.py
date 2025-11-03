"""Ingestion endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, status

from app.schemas import LogIngestPayload, LogIngestResponse
from app.tasks import process_log


router = APIRouter()


@router.post("/ingest", response_model=LogIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_log(payload: LogIngestPayload) -> LogIngestResponse:
    """Accept a log payload, enqueue processing, and return immediately."""

    payload_dict = payload.model_dump()
    payload_dict["attributes"] = payload.merged_attributes()
    if payload_dict.get("log_timestamp") is None:
        payload_dict["log_timestamp"] = datetime.now(timezone.utc).isoformat()

    task = process_log.delay(payload_dict)
    return LogIngestResponse(status="accepted", task_id=task.id)
