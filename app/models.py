"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

# Use JSONB on Postgres, fall back to generic JSON elsewhere (SQLite).
JSONType = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Analysis(Base):
    """A single speech-analysis run and its generated report card."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # For "continue as guest" sessions that are not tied to a user row.
    guest_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|done|failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw + derived data
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    words_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    filler_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fluency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full structured report card (filler breakdown, metrics, LLM insights).
    report: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User | None"] = relationship(back_populates="analyses")
