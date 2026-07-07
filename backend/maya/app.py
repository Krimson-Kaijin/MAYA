"""FastAPI application — JSON API + static serving of the built frontend.

Binds to localhost only. Everything the UI shows comes through these routes;
there are no background jobs and no hidden network calls.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .audit import AuditLogger
from .config import Config
from .db import Database
from .email_connectors import get_connector
from .files import FileIndexer, search_index
from .memory import MemoryManager
from .nlp import get_summarizer
from .orchestrator import ActionGate, Orchestrator
from .persona import Persona
from .policy import PolicyEngine


class ChatIn(BaseModel):
    text: str
    mode: str = "chat"                    # chat | voice
    session_id: str = "default"


class ConfirmIn(BaseModel):
    approve: bool


class MemoryIn(BaseModel):
    value: str
    key: str | None = None


class ToggleIn(BaseModel):
    enabled: bool


class SettingsIn(BaseModel):
    wit_level: str | None = Field(default=None, pattern="^(off|subtle|classic)$")
    tts_rate: float | None = Field(default=None, ge=0.5, le=2.0)
    voice_hint: str | None = None


class SummarizeIn(BaseModel):
    path: str
    mode: str = "medium"


class CompareIn(BaseModel):
    a: str
    b: str


class SendDraftIn(BaseModel):
    to: str
    subject: str
    body: str


def create_app(config: Config | None = None, db_path: str | None = None) -> FastAPI:
    config = config or Config.load()
    db = Database(db_path or (config.data_dir / "maya.db"))
    audit = AuditLogger(db)
    policy = PolicyEngine(config)
    indexer = FileIndexer(config, db, policy, audit)
    connector = get_connector(config)
    memory = MemoryManager(db, config, policy.classifier, audit)
    persona = Persona(
        config.personality,
        wit_level=db.kv_get("wit_level", config.wit_level),
        telugu_flair=bool(config.get("persona.telugu_flair", True)),
    )
    gate = ActionGate(policy, audit, config, on_files_changed=indexer.rebuild)
    orchestrator = Orchestrator(
        config=config, db=db, policy=policy, indexer=indexer, connector=connector,
        memory=memory, audit=audit, persona=persona, gate=gate,
        summarizer=get_summarizer(config),
    )
    indexer.rebuild()

    app = FastAPI(title="MAYA", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # vite dev
        allow_methods=["*"], allow_headers=["*"],
    )
    state = app.state
    state.config, state.db, state.orchestrator = config, db, orchestrator
    state.indexer, state.memory, state.audit = indexer, memory, audit
    state.gate, state.persona, state.connector = gate, persona, connector
    state.policy = policy

    # ------------------------------------------------------------------ chat --
    @app.post("/api/chat")
    def chat(body: ChatIn):
        return orchestrator.handle(body.text, mode=body.mode, session_id=body.session_id)

    # ------------------------------------------------------------------ files --
    @app.get("/api/files/search")
    def files_search(q: str = "", type: str | None = None, folder: str | None = None,
                     latest: bool = False):
        hits = search_index(db, q, ftype=type, folder=folder, latest=latest, limit=20)
        audit.log("files.search", detail=f"q='{q}' hits={len(hits)}")
        return {"hits": [h.to_dict() for h in hits]}

    @app.post("/api/files/summarize")
    def files_summarize(body: SummarizeIn):
        return orchestrator.summarize_path(body.path, body.mode)

    @app.post("/api/files/compare")
    def files_compare(body: CompareIn):
        return orchestrator.compare_paths(body.a, body.b)

    @app.post("/api/index/rebuild")
    def index_rebuild():
        return indexer.rebuild().to_dict()

    # ------------------------------------------------------------------ email --
    @app.get("/api/emails/digest")
    def emails_digest(session_id: str = "default"):
        return orchestrator.handle("summarize my emails", session_id=session_id)

    @app.post("/api/emails/send_draft")
    def send_draft(body: SendDraftIn):
        desc = f"Send email to {body.to} — “{body.subject}” (simulated: mock connector)"
        outcome = gate.submit("send_email", body.model_dump(), desc)
        return outcome

    # ------------------------------------------------------------------ briefing --
    @app.get("/api/briefing")
    def briefing(session_id: str = "default"):
        return orchestrator.handle("what should I prioritize today?", session_id=session_id)

    # ------------------------------------------------------------------ actions --
    @app.get("/api/actions/pending")
    def actions_pending():
        return {"pending": gate.pending()}

    @app.post("/api/actions/{action_id}/confirm")
    def actions_confirm(action_id: str, body: ConfirmIn):
        outcome = gate.confirm(action_id, body.approve)
        if outcome["status"] == "not_found":
            raise HTTPException(404, "No such pending action")
        return outcome

    # ------------------------------------------------------------------ memory --
    @app.get("/api/memory")
    def memory_list():
        return {"items": memory.list(), "enabled": memory.enabled}

    @app.post("/api/memory")
    def memory_add(body: MemoryIn):
        return memory.remember(body.value, key=body.key, source="settings")

    @app.delete("/api/memory/{memory_id}")
    def memory_delete(memory_id: int):
        if not memory.delete(memory_id):
            raise HTTPException(404, "No such memory")
        return {"deleted": memory_id}

    @app.post("/api/memory/enabled")
    def memory_toggle(body: ToggleIn):
        memory.set_enabled(body.enabled)
        return {"enabled": memory.enabled}

    # ------------------------------------------------------------------ audit --
    @app.get("/api/audit")
    def audit_recent(limit: int = 80, event: str | None = None):
        return {"entries": audit.recent(limit=limit, event_prefix=event)}

    # ------------------------------------------------------------------ meta --
    @app.get("/api/sources")
    def sources():
        return {
            "folders": [
                {"path": str(p), "exists": p.exists()} for p in config.approved_folders
            ],
            "denied_patterns": config.denied_patterns,
            "email": {
                "provider": connector.name, "status": connector.status,
                "note": connector.status_note, "labels": config.approved_labels,
            },
            "indexed_files": indexer.count(),
            "voice": {"engine": "Browser Web Speech API (audio never leaves your machine)",
                      "wake_phrases": config.wake_phrases},
        }

    @app.get("/api/settings")
    def settings_get():
        return {
            "wit_level": persona.wit_level,
            "telugu_flair": bool(config.get("persona.telugu_flair", True)),
            "memory_enabled": memory.enabled,
            "tts_rate": float(db.kv_get("tts_rate", str(config.get("voice.tts_rate", 1.0)))),
            "voice_hint": db.kv_get("voice_hint", config.get("voice.preferred_voice_hint", "en-IN")),
            "summarizer": orchestrator.summarizer.name,
        }

    @app.put("/api/settings")
    def settings_put(body: SettingsIn):
        if body.wit_level:
            persona.set_wit_level(body.wit_level)
            db.kv_set("wit_level", body.wit_level)
        if body.tts_rate is not None:
            db.kv_set("tts_rate", str(body.tts_rate))
        if body.voice_hint is not None:
            db.kv_set("voice_hint", body.voice_hint)
        audit.log("settings.update", detail=str(body.model_dump(exclude_none=True)))
        return settings_get()

    @app.get("/api/meta")
    def meta():
        return {
            "name": "MAYA", "expansion": "Modular Assistant for Your Actions",
            "tagline": config.personality.get("identity", {}).get("tagline", ""),
            "version": __version__,
        }

    # ---------------------------------------------------------- static frontend --
    dist = config.root / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        if (dist / "fonts").exists():
            app.mount("/fonts", StaticFiles(directory=dist / "fonts"), name="fonts")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
