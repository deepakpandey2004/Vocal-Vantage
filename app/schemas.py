"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_guest: bool = False


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    is_guest: bool
    created_at: datetime


# ---------- Analysis ----------
class FillerBreakdown(BaseModel):
    word: str
    count: int


class AnalysisMetrics(BaseModel):
    words_per_minute: float
    filler_rate_per_min: float
    vocabulary_diversity: float  # type-token ratio


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    error_message: str | None = None
    transcript: str | None = None
    duration_seconds: float | None = None
    word_count: int | None = None
    words_per_minute: float | None = None
    filler_count: int | None = None
    fluency_score: int | None = None
    report: dict[str, Any] | None = None
    created_at: datetime


class AnalysisListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    fluency_score: int | None = None
    words_per_minute: float | None = None
    created_at: datetime
