"""End-to-end retrieval augmented generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LogRecord
from app.schemas import LogQueryFilters, LogQueryRequest, LogQueryResponse
from app.schemas.logs import LogQueryContext, LogRecordOut
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm import LLMService, get_llm_service


@dataclass
class RetrievedLog:
    """Container for a log record and its similarity score."""

    record: LogRecord
    score: float

    def to_schema(self) -> LogQueryContext:
        return LogQueryContext(match_score=self.score, log=LogRecordOut(**self.record.to_dict()))


class RAGPipeline:
    """Coordinates embeddings, vector search, and LLM synthesis."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_service = embedding_service or get_embedding_service()
        self.llm_service = llm_service or get_llm_service()

    def _build_query(self, query_vector: Sequence[float], filters: LogQueryFilters, limit: int) -> Select:
        distance = LogRecord.embedding.cosine_distance(
            query_vector).label("score")

        stmt = select(LogRecord, distance).order_by(distance).limit(limit)

        if filters.service:
            stmt = stmt.where(LogRecord.service == filters.service)
        if filters.level:
            stmt = stmt.where(LogRecord.level == filters.level)
        if filters.start_time:
            stmt = stmt.where(LogRecord.log_timestamp >= filters.start_time)
        if filters.end_time:
            stmt = stmt.where(LogRecord.log_timestamp <= filters.end_time)
        return stmt

    def retrieve(self, session: Session, request: LogQueryRequest) -> List[RetrievedLog]:
        query_vector = self.embedding_service.embed_text(request.query)
        stmt = self._build_query(query_vector, request.filters, request.limit)
        results = session.execute(stmt).all()

        retrieved: List[RetrievedLog] = []
        for row in results:
            log, score = row
            retrieved.append(RetrievedLog(record=log, score=float(score)))
        return retrieved

    def answer(self, session: Session, request: LogQueryRequest) -> LogQueryResponse:
        retrieved = self.retrieve(session, request)
        logs_as_dict = [item.record.to_dict() for item in retrieved]
        answer = self.llm_service.generate(
            request.query, logs_as_dict[: self.settings.max_context_logs])

        contexts = [item.to_schema() for item in retrieved]
        return LogQueryResponse(
            answer=answer,
            logs=[context.log for context in contexts],
            contexts=contexts,
            requested_k=request.limit,
            used_k=len(retrieved),
        )
