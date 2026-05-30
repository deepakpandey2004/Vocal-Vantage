"""Unit tests for the linguistic analysis engine (no external calls)."""
from app.services.analyzer import analyze_transcript


def test_basic_metrics():
    transcript = "Hello everyone this is a clear and simple talk about speaking well today"
    # 13 words in ~10 seconds -> high WPM
    result = analyze_transcript(transcript, duration_seconds=10)
    assert result.word_count == 13
    assert result.words_per_minute > 0
    assert 0 <= result.fluency_score <= 100
    assert 0 < result.vocabulary_diversity <= 1


def test_filler_detection():
    transcript = "um so like you know this is um basically a test uh okay"
    result = analyze_transcript(transcript, duration_seconds=10)
    assert result.filler_count > 0
    words = {b["word"] for b in result.filler_breakdown}
    assert "um" in words
    assert "you know" in words


def test_empty_transcript():
    result = analyze_transcript("", duration_seconds=10)
    assert result.word_count == 0
    assert result.words_per_minute == 0
    assert result.fluency_score >= 0


def test_clean_speech_scores_higher_than_filler_heavy():
    clean = ("Welcome to todays presentation where we explore practical strategies "
             "for delivering memorable talks with clarity confidence and genuine impact")
    messy = "um uh um like so you know um uh basically like um so uh you know um"
    clean_result = analyze_transcript(clean, duration_seconds=10)
    messy_result = analyze_transcript(messy, duration_seconds=10)
    assert clean_result.fluency_score > messy_result.fluency_score
