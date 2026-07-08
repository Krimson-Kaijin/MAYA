# MAYA — Architecture Overview

A local web app: **FastAPI backend** (API + static serving) and a **React frontend**
(hand-built design system). One process, one port (8930), everything on localhost.
The brief allowed "a local web app if that simplifies delivery" — it does; the layout
and interactions are desktop-first and the API would survive a Tauri/Electron wrap
unchanged.

## Module map

```
                       ┌────────────────────────────────────────────┐
                       │  frontend/ (React)                         │
                       │  orb · chat · cards · views · drawer       │
                       │  voice.js: Web Speech STT/TTS (browser)    │
                       └──────────────────┬─────────────────────────┘
                                          │ JSON (localhost only; text, never audio)
                       ┌──────────────────▼─────────────────────────┐
                       │  app.py — FastAPI routes                   │
                       └──────────────────┬─────────────────────────┘
                       ┌──────────────────▼─────────────────────────┐
                       │  orchestrator/                             │
                       │   intents.py   rule-based command parser   │
                       │   orchestrator responses + session context │
                       │   actions.py   confirmation gate           │
                       └───┬───────┬──────────┬──────────┬──────────┘
                           │       │          │          │
              ┌────────────▼─┐ ┌───▼────┐ ┌───▼─────┐ ┌──▼────────┐
              │ files/       │ │ nlp/   │ │ email_  │ │ memory/   │
              │ parsers      │ │ summar │ │ connect │ │ (Fernet-  │
              │ indexer      │ │ tasks  │ │ mock ✓  │ │ encrypted)│
              │ search       │ │ compare│ │ gmail ✗ │ │           │
              └──────┬───────┘ └───▲────┘ │ digest  │ └─────▲─────┘
                     │             │      └───┬─────┘       │
        ┌────────────▼─────────────┴──────────▼─────────────┴──────┐
        │  policy/ — THE CHOKE POINT                               │
        │  sensitivity.py  SAFE / SENSITIVE / BLOCKED classifier   │
        │  redaction.py    masks spans before any NLP or display   │
        │  engine.py       path allowlist · action risk table      │
        └────────────┬─────────────────────────────────────────────┘
                     │ every event
        ┌────────────▼──────────┐   ┌───────────────────────────────┐
        │  audit/ append-only   │   │  persona/ tone + guardrails   │
        └───────────────────────┘   │  (wraps every reply)          │
                                    └───────────────────────────────┘
        db.py — SQLite: file_index · memory · audit · kv     config.py — YAML configs
```

## The policy pipeline (the part that matters)

Every piece of content — file text at index time, email body at digest time, a value
the user asks MAYA to remember — passes through `PolicyEngine.prepare_text()`:

1. **Classify** (`sensitivity.py`): structural detectors (Luhn-valid card numbers,
   PAN, IFSC, Aadhaar-shaped IDs, OTP codes, SSN) + keyword/sender rules from
   `config/policy.yaml` → `SAFE | SENSITIVE | BLOCKED` with categories.
2. **Gate**: `BLOCKED` → the caller gets `allowed=False` and *no text at all*.
   Blocked files are indexed metadata-only; blocked emails become category-level
   notices; blocked memory writes are refused. There is no code path that carries
   blocked content further.
3. **Redact** (`redaction.py`): for allowed content, sensitive spans are replaced
   with `[REDACTED:TYPE]` *before* the summarizer, the index, or the UI sees it.

Downstream modules (`nlp/`, `files/search`, digest, UI cards) only ever operate on
prepared text. That single choke point is what the privacy tests assert against.

## Actions and the confirmation gate

`config/policy.yaml` declares three risk classes:
- **safe** (search, read, summarize, draft, digest, briefing…) — run immediately;
- **gated** (`move_file`, `delete_file`, `send_email`) — become a `PendingAction`
  showing the exact operation; executed only on explicit approval (drawer button or
  spoken "confirm"), expire after 3 minutes, and always audit-log request/outcome;
- **forbidden** (banking/payment/brokerage/payroll/password-manager access, bulk
  delete…) — refused outright; unknown action types fail closed to *gated*.

Delete is reversible by construction (move to `data/trash/`); "send" writes to a
simulated outbox file clearly marked as such.

## Voice

STT and TTS run **in the browser** (Web Speech API / speechSynthesis) — a deliberate
privacy choice: the backend never receives audio, only final transcripts posted to
`/api/chat` with `mode="voice"`. Wake-phrase mode is a continuous recognizer that
ignores utterances not starting with "Maya". Starting to talk cancels playback
(interruption). `backend/maya/voice/` holds the STT/TTS abstractions + test mocks and
is the seam for local engines (whisper.cpp / Piper) later.

## Persona

`persona/engine.py` composes every reply as *core answer first, optional quip second*.
Quips come only from reviewed pools in `config/personality.yaml`; the engine enforces
a wit budget (ratio per level, never two in a row, no repeats in a 6-quip window) and
**zero humor** whenever content is SENSITIVE/BLOCKED or the reply is a refusal. Wit
level (off/subtle/classic) is a runtime setting.

## Data & state

- **SQLite** (`data/maya.db`): file index (redacted text only), encrypted memory,
  append-only audit log, runtime settings overrides.
- **Session context** (per browser session, in-process only): last search hits,
  last digest items — enables "summarize the second one", "compare these two".
  Never persisted.
- **`data/`** is gitignored: DB, Fernet key (`maya.key`, 0600), trash, outbox.

## Testing

91 pytest tests run every module against a throwaway copy of the sample workspace in
`tmp_path`, so gated actions can actually execute (and be reverted) without touching
the repo. `test_api.py` drives the real FastAPI app end-to-end via TestClient.
