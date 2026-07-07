"""Email digest: bucketing, shielding of blocked messages, no content leaks."""

import json

from maya.email_connectors import build_digest, get_connector


def _digest(cfg, policy):
    emails = get_connector(cfg).list_messages()
    return build_digest(emails, policy, cfg.vip_senders)


def test_blocked_emails_are_shielded(cfg, policy):
    d = _digest(cfg, policy)
    # OTP (m-1005), payslip (m-1006), card statement (m-1011)
    assert d["counts"]["shielded"] == 3
    cats = {c for it in d["buckets"]["shielded"] for c in it["categories"]}
    assert {"credentials", "payroll"} <= cats


def test_no_blocked_content_leaks(cfg, policy):
    dump = json.dumps(_digest(cfg, policy))
    assert "482913" not in dump                 # the OTP code
    assert "1,84,000" not in dump               # salary figure
    assert "47,832" not in dump                 # card statement amount
    assert "OTP for your net banking" not in dump  # blocked subject line


def test_urgent_bucket(cfg, policy):
    d = _digest(cfg, policy)
    subjects = " | ".join(it["subject"] for it in d["buckets"]["urgent"])
    assert "Meridian" in subjects               # the escalation
    assert "Board" in subjects                  # VIP (CEO) + deadline language


def test_meetings_bucket_includes_sensitive_appointment(cfg, policy):
    d = _digest(cfg, policy)
    meetings = d["buckets"]["meetings"]
    assert any("kickoff" in it["subject"].lower() for it in meetings)
    clinic = [it for it in meetings if it["sensitivity"] == "SENSITIVE"]
    assert clinic, "health appointment should be present but flagged SENSITIVE"


def test_noise_bucket(cfg, policy):
    d = _digest(cfg, policy)
    assert len(d["buckets"]["noise"]) >= 2      # newsletter + promo


def test_every_visible_item_has_explanation(cfg, policy):
    d = _digest(cfg, policy)
    for bucket in ("urgent", "action", "meetings", "follow_ups", "noise"):
        for it in d["buckets"][bucket]:
            assert it["why"], f"item {it['id']} lacks a 'why' explanation"


def test_digest_source_marked_as_mock(cfg, policy):
    assert "Mock" in _digest(cfg, policy)["source_note"]
