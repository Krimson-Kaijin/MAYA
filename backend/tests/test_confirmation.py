"""Confirmation gating: nothing with side effects happens without approval."""

import json
from pathlib import Path


def _workspace(cfg) -> Path:
    return cfg.approved_folders[0]


def test_delete_requires_confirmation(orchestrator, cfg):
    target = _workspace(cfg) / "notes" / "festival_campaign_ideas.md"
    assert target.exists()
    resp = orchestrator.handle("delete the festival campaign ideas")
    assert resp["pending_action"] is not None
    assert resp["pending_action"]["status"] == "pending"
    assert "confirmation" in resp["reply"].lower() or "confirm" in resp["reply"].lower()
    assert target.exists(), "file must be untouched before approval"


def test_cancel_leaves_file_alone(orchestrator, cfg):
    target = _workspace(cfg) / "notes" / "festival_campaign_ideas.md"
    orchestrator.handle("delete the festival campaign ideas")
    resp = orchestrator.handle("cancel")
    assert "cancel" in resp["reply"].lower()
    assert target.exists()


def test_confirm_executes_reversible_delete(orchestrator, cfg):
    target = _workspace(cfg) / "notes" / "festival_campaign_ideas.md"
    orchestrator.handle("delete the festival campaign ideas")
    resp = orchestrator.handle("confirm")
    assert not target.exists()
    trash = cfg.data_dir / "trash"
    assert any("festival_campaign_ideas" in p.name for p in trash.iterdir())
    assert "trash" in resp["reply"].lower()


def test_move_stays_inside_approved_folders(orchestrator, cfg, gate):
    src = _workspace(cfg) / "reports" / "q2_vendor_review.txt"
    orchestrator.handle("move the q2 vendor review to archive")
    pending = gate.pending()
    assert len(pending) == 1
    orchestrator.handle("confirm")
    assert (_workspace(cfg) / "archive" / "q2_vendor_review.txt").exists()
    assert not src.exists()


def test_move_outside_approved_folders_fails(gate, cfg, tmp_path):
    src = _workspace(cfg) / "sops" / "logistics_sop_v2.md"
    outcome = gate.submit("move_file",
                          {"src": str(src), "dest_dir": str(tmp_path / "elsewhere")},
                          "Move SOP outside the workspace")
    result = gate.confirm(outcome["action"]["id"], approve=True)
    assert result["status"] == "failed"
    assert src.exists()


def test_forbidden_action_is_refused(gate):
    outcome = gate.submit("access_banking", {}, "read bank account")
    assert outcome["status"] == "forbidden"


def test_send_email_is_simulated_and_gated(gate, cfg):
    outcome = gate.submit(
        "send_email",
        {"to": "Priya", "subject": "Re: Meridian", "body": "Draft body"},
        "Send email to Priya")
    assert outcome["status"] == "pending"
    outbox = cfg.data_dir / "outbox.json"
    assert not outbox.exists(), "nothing written before approval"
    gate.confirm(outcome["action"]["id"], approve=True)
    entries = json.loads(outbox.read_text())
    assert entries[0]["transport"].startswith("SIMULATED")


def test_pending_actions_expire(gate, cfg, monkeypatch):
    outcome = gate.submit("delete_file",
                          {"path": str(_workspace(cfg) / "sops" / "logistics_sop_v2.md")},
                          "Delete old SOP")
    action_id = outcome["action"]["id"]
    import time as _time
    real = _time.time
    monkeypatch.setattr("maya.orchestrator.actions.time.time",
                        lambda: real() + 10_000)
    assert gate.pending() == []
    assert gate.confirm(action_id, approve=True)["status"] == "expired"


def test_gate_activity_is_audited(orchestrator, audit):
    orchestrator.handle("delete the shipment delays csv")
    orchestrator.handle("confirm")
    events = [e["event"] for e in audit.recent()]
    assert "action.requested" in events
    assert "action.executed" in events
