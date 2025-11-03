"""SQLAlchemy models for Logiq."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


EMBEDDING_DIM = 384


class Base(DeclarativeBase):
    """Base declarative model with metadata shared across tables."""


class LogRecord(Base):
    """Primary log storage table containing raw text and embedding."""

    __tablename__ = "logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    log_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    service: Mapped[str] = mapped_column(
        String(length=255), index=True, nullable=False)
    level: Mapped[str] = mapped_column(
        String(length=50), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM))

    def to_dict(self) -> dict:
        """Serialize the log record into primitive types."""

        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "log_timestamp": self.log_timestamp.isoformat() if self.log_timestamp else None,
            "service": self.service,
            "level": self.level,
            "message": self.message,
            "attributes": self.attributes or {},
        }
