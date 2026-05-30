"""LLM feedback generation via Google Gemini.

Takes the computed metrics + transcript and asks Gemini to produce a
structured JSON report card (strengths, improvements, actionable tips,
overall summary). Falls back to a rule-based report when no key / mock mode,
so the feature is always demoable.
"""
import json
import logging
from typing import Any

from app.config import settings
from app.services.analyzer import AnalysisResult

logger = logging.getLogger("vocal_vantage.feedback")


_PROMPT = """You are an expert public-speaking coach. Analyse the speaker's
performance using the transcript and metrics below, then return ONLY valid
JSON (no markdown fences) matching this exact schema:

{{
  "summary": "2-3 sentence overall assessment",
  "strengths": ["short bullet", "short bullet"],
  "improvements": ["short bullet", "short bullet"],
  "actionable_tips": ["specific tip", "specific tip", "specific tip"],
  "tone": "one word describing delivery tone",
  "confidence_estimate": "low|medium|high"
}}

METRICS:
- Words per minute: {wpm}
- Filler words used: {filler_count} ({filler_rate}/min)
- Top fillers: {top_fillers}
- Vocabulary diversity (type-token ratio): {diversity}
- Fluency score: {score}/100

TRANSCRIPT:
\"\"\"{transcript}\"\"\"
"""


def _rule_based_feedback(result: AnalysisResult) -> dict[str, Any]:
    strengths, improvements, tips = [], [], []

    if 120 <= result.words_per_minute <= 165:
        strengths.append("Your speaking pace is in the ideal, easy-to-follow range.")
    elif result.words_per_minute < 120:
        improvements.append("Your pace is a little slow; add energy to stay engaging.")
        tips.append("Practise reading aloud with a metronome target of ~140 WPM.")
    else:
        improvements.append("You're speaking quite fast; slow down for clarity.")
        tips.append("Insert deliberate pauses at the end of each key point.")

    if result.filler_rate_per_min <= 2:
        strengths.append("You use very few filler words — clean, confident delivery.")
    else:
        top = result.filler_breakdown[0]["word"] if result.filler_breakdown else "um"
        improvements.append(f"Filler words (especially '{top}') reduce your authority.")
        tips.append("Replace fillers with a short silent pause to gather your thoughts.")

    if result.vocabulary_diversity >= 0.5:
        strengths.append("Rich and varied vocabulary keeps the audience interested.")
    else:
        improvements.append("Vocabulary is a bit repetitive.")
        tips.append("Prepare 2-3 synonyms for your most-used key terms.")

    if not tips:
        tips.append("Record yourself weekly and track your fluency score over time.")

    confidence = "high" if result.fluency_score >= 80 else (
        "medium" if result.fluency_score >= 60 else "low"
    )

    return {
        "summary": (
            f"You scored {result.fluency_score}/100 for fluency. "
            f"You spoke at {result.words_per_minute} WPM with "
            f"{result.filler_count} filler words detected."
        ),
        "strengths": strengths or ["Clear effort and a complete delivery."],
        "improvements": improvements or ["Keep refining for an even stronger delivery."],
        "actionable_tips": tips,
        "tone": "conversational",
        "confidence_estimate": confidence,
        "generated_by": "rule_based",
    }


def _safe_parse_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        # Try to extract the outermost JSON object.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
    return None


async def generate_feedback(result: AnalysisResult) -> dict[str, Any]:
    if settings.ai_mock_mode or not settings.gemini_api_key:
        logger.info("Feedback running in rule-based/mock mode.")
        return _rule_based_feedback(result)

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        top_fillers = ", ".join(
            f"{b['word']} ({b['count']})" for b in result.filler_breakdown[:5]
        ) or "none"

        prompt = _PROMPT.format(
            wpm=result.words_per_minute,
            filler_count=result.filler_count,
            filler_rate=result.filler_rate_per_min,
            top_fillers=top_fillers,
            diversity=result.vocabulary_diversity,
            score=result.fluency_score,
            transcript=result.transcript[:6000],
        )

        # Run the blocking SDK call in a thread so we don't block the loop.
        import asyncio

        resp = await asyncio.to_thread(model.generate_content, prompt)
        parsed = _safe_parse_json(resp.text or "")
        if parsed:
            parsed["generated_by"] = settings.gemini_model
            return parsed
        logger.warning("Gemini returned unparseable JSON; using rule-based fallback.")
        return _rule_based_feedback(result)
    except Exception as exc:
        logger.exception("Gemini feedback failed: %s", exc)
        return _rule_based_feedback(result)
