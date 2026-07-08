"""End-to-end API tests through FastAPI's TestClient."""

import pytest
from fastapi.testclient import TestClient

from maya.app import create_app


@pytest.fixture()
def client(cfg):
    app = create_app(config=cfg, db_path=":memory:")
    return TestClient(app)


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["name"] == "MAYA"
    assert body["expansion"] == "Modular Assistant for Your Actions"


def test_chat_find_flow(client):
    r = client.post("/api/chat", json={"text": "Maya, find the latest logistics SOP"})
    body = r.json()
    assert body["intent"] == "find_file"
    assert body["cards"][0]["type"] == "files"
    assert body["cards"][0]["items"][0]["name"] == "logistics_sop_v3.md"
    assert body["accessed"]


def test_chat_then_ordinal_summarize(client):
    client.post("/api/chat", json={"text": "find the logistics sop"})
    r = client.post("/api/chat", json={"text": "summarize the first one"})
    body = r.json()
    assert body["intent"] == "summarize_file"
    assert body["cards"][0]["type"] == "summary"


def test_briefing_endpoint(client):
    body = client.get("/api/briefing").json()
    card = body["cards"][0]
    assert card["type"] == "briefing"
    assert card["suggestions"]
    assert card["recent_files"]
    assert card["shielded_count"] == 3


def test_digest_endpoint_shields_blocked(client):
    body = client.get("/api/emails/digest").json()
    card = body["cards"][0]
    assert card["counts"]["shielded"] == 3
    assert "482913" not in str(body)


def test_files_summarize_by_path(client):
    hits = client.get("/api/files/search", params={"q": "vendor review"}).json()["hits"]
    path = hits[0]["path"]
    body = client.post("/api/files/summarize", json={"path": path, "mode": "short"}).json()
    assert body["cards"][0]["summary"]["mode"] == "short"


def test_compare_by_path(client):
    hits = client.get("/api/files/search", params={"q": "logistics sop"}).json()["hits"]
    paths = [h["path"] for h in hits[:2]]
    body = client.post("/api/files/compare", json={"a": paths[0], "b": paths[1]}).json()
    assert body["cards"][0]["type"] == "compare"
    assert body["cards"][0]["version_note"]


def test_action_gate_over_api(client, cfg):
    target = cfg.approved_folders[0] / "notes" / "festival_campaign_ideas.md"
    r = client.post("/api/chat", json={"text": "delete the festival campaign ideas"}).json()
    action_id = r["pending_action"]["id"]
    assert target.exists()

    pending = client.get("/api/actions/pending").json()["pending"]
    assert pending and pending[0]["id"] == action_id

    out = client.post(f"/api/actions/{action_id}/confirm", json={"approve": False}).json()
    assert out["status"] == "cancelled"
    assert target.exists()

    r2 = client.post("/api/chat", json={"text": "delete the festival campaign ideas"}).json()
    out2 = client.post(f"/api/actions/{r2['pending_action']['id']}/confirm",
                       json={"approve": True}).json()
    assert out2["status"] == "executed"
    assert not target.exists()


def test_memory_roundtrip(client):
    assert client.post("/api/memory", json={"value": "prefers evening briefings"}).json()["stored"]
    items = client.get("/api/memory").json()["items"]
    assert any("evening briefings" in i["value"] for i in items)
    refused = client.post("/api/memory", json={"value": "OTP is 482913"}).json()
    assert not refused["stored"]
    mid = items[0]["id"]
    assert client.delete(f"/api/memory/{mid}").status_code == 200
    client.post("/api/memory/enabled", json={"enabled": False})
    assert client.get("/api/memory").json()["enabled"] is False


def test_sources_shows_mock_status(client):
    body = client.get("/api/sources").json()
    assert body["email"]["status"] == "mock"
    assert body["indexed_files"] > 0
    assert body["folders"]


def test_audit_populated(client):
    client.get("/api/emails/digest")
    entries = client.get("/api/audit").json()["entries"]
    assert any(e["event"] == "email.shielded" for e in entries)


def test_settings_update(client):
    body = client.put("/api/settings", json={"wit_level": "off"}).json()
    assert body["wit_level"] == "off"
