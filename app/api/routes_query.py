"""Query endpoints for natural-language search."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas import LogQueryRequest, LogQueryResponse
from app.services.rag import RAGPipeline


router = APIRouter()
pipeline = RAGPipeline()


@router.post("/query", response_model=LogQueryResponse)
async def query_logs(
    request: LogQueryRequest, session: Session = Depends(get_db_session)
) -> LogQueryResponse:
    """Return an answer generated from relevant logs."""

    return pipeline.answer(session, request)
