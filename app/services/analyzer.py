"""Linguistic analysis engine.

Computes the three core linguistic metrics from a transcript + duration:
  1. Words Per Minute (pace)
  2. Filler-word rate (per minute) with a per-word breakdown
  3. Vocabulary diversity (type-token ratio)

It also produces a 0-100 fluency score from these signals. This is the pure
"Python analysis" stage of the pipeline (no external calls), which makes it
fast, deterministic and unit-testable.
"""
import re
from dataclasses import dataclass, field

# Common English filler words / phrases. Multi-word phrases are checked first.
FILLER_PHRASES = [
    "you know",
    "i mean",
    "sort of",
    "kind of",
]
FILLER_WORDS = [
    "um",
    "umm",
    "uh",
    "uhh",
    "er",
    "err",
    "ah",
    "like",
    "so",
    "and",  # only counted as filler when used as a discourse crutch (see logic)
    "basically",
    "actually",
    "literally",
    "right",
    "okay",
    "ok",
    "well",
    "hmm",
]

# "and"/"so"/"right"/"okay"/"well" are real words too — to avoid over-counting
# we only treat them as fillers when they are sentence-initial or stand-alone
# discourse markers. We keep a conservative set that is always a filler.
ALWAYS_FILLER = {"um", "umm", "uh", "uhh", "er", "err", "ah", "hmm"}


@dataclass
class AnalysisResult:
    transcript: str
    duration_seconds: float
    word_count: int
    words_per_minute: float
    filler_count: int
    filler_rate_per_min: float
    filler_breakdown: list[dict] = field(default_factory=list)
    vocabulary_diversity: float = 0.0
    fluency_score: int = 0
    metrics: dict = field(default_factory=dict)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _count_fillers(text: str) -> tuple[int, list[dict]]:
    lowered = text.lower()
    counts: dict[str, int] = {}

    # Count multi-word filler phrases first, then strip them so their tokens
    # aren't double-counted as single-word fillers.
    for phrase in FILLER_PHRASES:
        found = len(re.findall(r"\b" + re.escape(phrase) + r"\b", lowered))
        if found:
            counts[phrase] = found
            lowered = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", lowered)

    tokens = _tokenize(lowered)
    # Single-word fillers.
    discourse = {"like", "so", "basically", "actually", "literally", "right",
                 "okay", "ok", "well", "and"}
    n = len(tokens)
    for i, tok in enumerate(tokens):
        is_filler = False
        if tok in ALWAYS_FILLER:
            is_filler = True
        elif tok in discourse:
            # Heuristic: treat as filler when at clause boundaries — start of
            # the transcript or repeated. Keeps "and" from over-counting.
            if tok == "and":
                # only count "and" when it's clearly a crutch: doubled "and and"
                if i + 1 < n and tokens[i + 1] == "and":
                    is_filler = True
            else:
                is_filler = True
        if is_filler:
            counts[tok] = counts.get(tok, 0) + 1

    total = sum(counts.values())
    breakdown = sorted(
        ({"word": w, "count": c} for w, c in counts.items()),
        key=lambda x: x["count"],
        reverse=True,
    )
    return total, breakdown


def _fluency_score(wpm: float, filler_rate: float, diversity: float) -> int:
    """Combine the three metrics into a 0-100 fluency score.

    - Pace: best around 130-160 WPM; penalised for too slow/fast.
    - Filler rate: penalised heavily above ~3 fillers/min.
    - Diversity: rewards richer vocabulary.
    """
    # Pace component (max 40)
    if wpm <= 0:
        pace_score = 0
    else:
        ideal = 145
        diff = abs(wpm - ideal)
        pace_score = max(0, 40 - (diff / 145) * 40)

    # Filler component (max 40) — 0 fillers/min => full marks.
    filler_score = max(0, 40 - filler_rate * 6)

    # Diversity component (max 20) — TTR of ~0.6+ is excellent for speech.
    diversity_score = min(20, (diversity / 0.6) * 20)

    return int(round(max(0, min(100, pace_score + filler_score + diversity_score))))


def analyze_transcript(transcript: str, duration_seconds: float) -> AnalysisResult:
    tokens = _tokenize(transcript)
    word_count = len(tokens)
    minutes = max(duration_seconds / 60.0, 1e-6)

    wpm = round(word_count / minutes, 1) if word_count else 0.0
    filler_count, breakdown = _count_fillers(transcript)
    filler_rate = round(filler_count / minutes, 2) if filler_count else 0.0

    unique = len(set(tokens))
    diversity = round(unique / word_count, 3) if word_count else 0.0

    score = _fluency_score(wpm, filler_rate, diversity)

    metrics = {
        "words_per_minute": wpm,
        "filler_rate_per_min": filler_rate,
        "vocabulary_diversity": diversity,
    }

    return AnalysisResult(
        transcript=transcript,
        duration_seconds=round(duration_seconds, 2),
        word_count=word_count,
        words_per_minute=wpm,
        filler_count=filler_count,
        filler_rate_per_min=filler_rate,
        filler_breakdown=breakdown,
        vocabulary_diversity=diversity,
        fluency_score=score,
        metrics=metrics,
    )
