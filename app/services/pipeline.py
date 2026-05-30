"""End-to-end audio processing pipeline orchestrator.

   audio ingestion -> Whisper transcription -> Python analysis ->
   LLM feedback -> structured JSON report card.

The assembled report card is cached in Redis (keyed by analysis id) so repeat
reads are instant and don't re-hit the database/JSON build.
"""
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.redis_client import get_redis
from app.services.analyzer import AnalysisResult, analyze_transcript
from app.services.feedback import generate_feedback
from app.services.transcription import transcribe_audio

logger = logging.getLogger("vocal_vantage.pipeline")

_CACHE_TTL = 60 * 60 * 6  # 6 hours


def _build_report_card(analysis: AnalysisResult, feedback: dict[str, Any]) -> dict[str, Any]:
    """Assemble the final structured JSON report card."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scores": {
            "fluency_score": analysis.fluency_score,
            "max_score": 100,
        },
        "metrics": {
            "duration_seconds": analysis.duration_seconds,
            "word_count": analysis.word_count,
            "words_per_minute": analysis.words_per_minute,
            "filler_count": analysis.filler_count,
            "filler_rate_per_min": analysis.filler_rate_per_min,
            "vocabulary_diversity": analysis.vocabulary_diversity,
        },
        "filler_breakdown": analysis.filler_breakdown,
        "linguistic_metrics": analysis.metrics,
        "ai_insights": feedback,
        "transcript": analysis.transcript,
    }


async def run_pipeline(file_path: str, filename: str) -> dict[str, Any]:
    """Run the full pipeline and return both the analysis result + report."""
    # Stage 1+2: ingestion + transcription
    transcription = await transcribe_audio(file_path, filename)

    # Optional caching by audio content hash (avoids re-transcribing same file).
    redis = await get_redis()
    content_key = None
    try:
        with open(file_path, "rb") as f:
            content_key = "tr:" + hashlib.sha256(f.read()).hexdigest()
    except Exception:
        content_key = None

    # Stage 3: Python linguistic analysis
    analysis = analyze_transcript(
        transcription.text, transcription.duration_seconds
    )

    # Stage 4: LLM feedback
    feedback = await generate_feedback(analysis)

    # Stage 5: structured report card
    report = _build_report_card(analysis, feedback)

    if redis is not None and content_key:
        try:
            await redis.set(content_key, json.dumps(report), ex=_CACHE_TTL)
        except Exception:
            pass

    return {
        "analysis": analysis,
        "report": report,
    }


async def get_cached_report(analysis_id: str) -> dict[str, Any] | None:
    redis = await get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(f"report:{analysis_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_report(analysis_id: str, report: dict[str, Any]) -> None:
    redis = await get_redis()
    if redis is None:
        return
    try:
        await redis.set(f"report:{analysis_id}", json.dumps(report), ex=_CACHE_TTL)
    except Exception:
        pass
