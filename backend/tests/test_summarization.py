"""Summarization modes, task extraction, and the blocked-document refusal."""

from pathlib import Path

from maya.nlp.summarizer import ExtractiveSummarizer
from maya.nlp import tasks

REPO = Path(__file__).resolve().parents[2]
REVIEW = (REPO / "sample_data/workspace/reports/q2_vendor_review.txt").read_text()
MEETING = (REPO / "sample_data/workspace/meetings/2026-07-06_ops_sync.md").read_text()


def test_modes_scale_length():
    s = ExtractiveSummarizer()
    short = s.summarize(REVIEW, "short")
    medium = s.summarize(REVIEW, "medium")
    detailed = s.summarize(REVIEW, "detailed")
    assert len(short.bullets) <= len(medium.bullets) <= len(detailed.bullets)
    assert 1 <= len(short.bullets) <= 2
    assert short.headline
    assert short.original_words > 200


def test_summary_is_deterministic():
    s = ExtractiveSummarizer()
    assert s.summarize(REVIEW, "medium").bullets == s.summarize(REVIEW, "medium").bullets


def test_summary_sentences_come_from_source():
    s = ExtractiveSummarizer()
    for b in s.summarize(REVIEW, "medium").bullets:
        assert b[:40] in REVIEW.replace("\n", " ")


def test_action_items_from_meeting_notes():
    items = tasks.extract_action_items(MEETING)
    assert len(items) >= 5
    assert any("Meridian recovery plan" in i for i in items)


def test_deadlines_extracted():
    found = " ".join(tasks.extract_deadlines(MEETING)).lower()
    assert "2026-07-08" in found
    assert "july 15" in found


def test_risks_extracted():
    risks = tasks.extract_risks(MEETING)
    assert risks and any("SLA penalty" in r for r in risks)


def test_entities_extracted():
    ents = tasks.extract_entities(MEETING)
    assert any("Meridian" in e for e in ents)


def test_blocked_document_summarization_refused(orchestrator):
    resp = orchestrator.handle("summarize the bank statement")
    assert resp["privacy"]["level"] == "BLOCKED"
    assert "privacy policy" in resp["reply"]
    assert "501000234891" not in str(resp)   # account number never leaks
    assert resp["cards"] == []
