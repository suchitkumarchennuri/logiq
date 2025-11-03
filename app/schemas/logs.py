"""Pydantic schemas for log ingestion and representation."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class LogIngestPayload(BaseModel):
    """Schema used by the `/ingest` endpoint."""

    service: str = Field(..., examples=["auth-api"])
    level: str = Field(..., examples=["ERROR"])
    message: str = Field(..., examples=["User 501 failed login"])
    log_timestamp: Optional[datetime] = Field(
        default=None, description="Timestamp provided by the emitting service"
    )
    attributes: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    def merged_attributes(self) -> Dict[str, Any]:
        """Return attributes combined with any arbitrary extras sent by the client."""

        extras = getattr(self, "model_extra", {}) or {}
        merged = {**extras}
        merged.update(self.attributes or {})
        # Remove reserved keys if they slipped into extras.
        for reserved in ("service", "level", "message", "log_timestamp", "attributes"):
            merged.pop(reserved, None)
        return merged


class LogIngestResponse(BaseModel):
    """Standard acknowledgement returned by `/ingest`."""

    status: str = Field(default="accepted")
    task_id: Optional[str] = None


class LogRecordOut(BaseModel):
    """Shape of a log record returned via the API."""

    id: str
    created_at: datetime
    log_timestamp: datetime
    service: str
    level: str
    message: str
    attributes: Dict[str, Any]


class LogQueryContext(BaseModel):
    """Metadata about the retrieval step that fed the LLM."""

    match_score: float
    log: LogRecordOut
