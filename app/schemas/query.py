"""Schemas for natural-language log queries."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.logs import LogQueryContext, LogRecordOut


class LogQueryFilters(BaseModel):
    """Optional filters that can be applied during retrieval."""

    service: Optional[str] = Field(default=None)
    level: Optional[str] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)


class LogQueryRequest(BaseModel):
    """Schema accepted by `/query`."""

    query: str = Field(...,
                       description="Natural-language question about ingested logs")
    filters: LogQueryFilters = Field(default_factory=LogQueryFilters)
    limit: int = Field(default=5, ge=1, le=50)


class LogQueryResponse(BaseModel):
    """Full payload returned after performing a query."""

    answer: str
    logs: List[LogRecordOut]
    contexts: List[LogQueryContext]
    requested_k: int
    used_k: int
