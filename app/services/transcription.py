"""Speech-to-text transcription (Groq free Whisper, or OpenAI paid)."""
import logging
import os
import wave
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("vocal_vantage.transcription")

_MOCK_TRANSCRIPT = (
    "Um, hello everyone and thanks for joining today. So, like, I want to talk "
    "about, uh, how we can improve our public speaking. You know, the thing is, "
    "um, practice really matters and, like, getting feedback is super important."
)


@dataclass
class TranscriptionResult:
    text: str
    duration_seconds: float

def _estimate_duration(file_path: str) -> float:
    try:
        with wave.open(file_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate:
                return round(frames / float(rate), 2)
    except Exception:
        pass
    try:
        size = os.path.getsize(file_path)
        return round(size / 16000.0, 2)
    except Exception:
        return 0.0


def _pick_provider() -> str:
    provider = (settings.transcription_provider or "auto").lower()
    if provider == "groq":
        return "groq" if settings.groq_api_key else "none"
    if provider == "openai":
        return "openai" if settings.openai_api_key else "none"
    if settings.groq_api_key:
        return "groq"
    if settings.openai_api_key:
        return "openai"
    return "none"

def _transcribe_groq(file_path: str) -> str:
    from groq import Groq

    client = Groq(api_key=settings.groq_api_key)
    with open(file_path, "rb") as audio_file:
        resp = client.audio.transcriptions.create(
            model=settings.groq_whisper_model,
            file=audio_file,
            response_format="json",
        )
    return (getattr(resp, "text", "") or "").strip()


async def _transcribe_openai(file_path: str):
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    with open(file_path, "rb") as audio_file:
        resp = await client.audio.transcriptions.create(
            model=settings.openai_whisper_model,
            file=audio_file,
            response_format="verbose_json",
        )
    text = (getattr(resp, "text", "") or "").strip()
    return text, getattr(resp, "duration", None)


async def transcribe_audio(file_path: str, filename: str) -> TranscriptionResult:
    duration = _estimate_duration(file_path)
    provider = _pick_provider()

    if settings.ai_mock_mode or provider == "none":
        logger.info("Transcription running in MOCK mode for %s", filename)
        return TranscriptionResult(text=_MOCK_TRANSCRIPT, duration_seconds=duration or 42.0)

    try:
        if provider == "groq":
            import asyncio
            logger.info("Transcribing %s via Groq Whisper", filename)
            text = await asyncio.to_thread(_transcribe_groq, file_path)
            return TranscriptionResult(text=text, duration_seconds=duration)
        else:
            logger.info("Transcribing %s via OpenAI Whisper", filename)
            text, api_duration = await _transcribe_openai(file_path)
            if api_duration:
                duration = float(api_duration)
            return TranscriptionResult(text=text, duration_seconds=duration)
    except Exception as exc:
        logger.exception("Transcription failed: %s", exc)
        raise RuntimeError(f"Transcription failed: {exc}") from exc