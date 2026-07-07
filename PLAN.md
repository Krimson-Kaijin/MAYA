# MAYA — Implementation Plan

> **MAYA** — *Modular Assistant for Your Actions*. A privacy-first, voice-interactive,
> desktop-style personal AI assistant with a Telugu-inspired feminine identity.

This plan was written before implementation, per the build brief. It defines scope,
module boundaries, the privacy model, and assumptions. See `PROGRESS.md` for live status
and `TODO.md` for the work checklist.

---

## 1. Delivery shape

**A local web app**: a FastAPI backend that serves both the JSON API and the built React
frontend at `http://localhost:8930`. The brief allows "a local web app if that simplifies
delivery" — it does. No Electron/Tauri shell; the app is desktop-first in layout and
interaction, and could be wrapped in Tauri later without touching the API.

Everything runs locally. There are **no external service calls at runtime**. Summarization
is local extractive NLP (clearly documented — not an LLM). Email is a **mock connector**
with realistic sample data (clearly marked in the UI). Voice uses the browser's Web Speech
API (real STT/TTS where the browser supports it) behind a backend abstraction.

## 2. Module boundaries

```
backend/maya/
├── app.py                  FastAPI app factory + routes + static serving (UI layer contract)
├── config.py               Loads config/*.yaml, resolves paths, holds Settings
├── db.py                   SQLite helper (settings, memory, audit, file index)
├── orchestrator/
│   ├── intents.py          Rule-based intent parser (voice/chat commands → Intent)
│   ├── orchestrator.py     Routes intents → skills; builds replies via persona; session context
│   └── actions.py          Pending-action registry + confirmation gate for risky actions
├── files/
│   ├── parsers.py          TXT / MD / CSV / PDF / DOCX text extraction
│   ├── indexer.py          Walks *approved* folders only; SQLite-backed index
│   └── search.py           Keyword search with type/folder/date filters + ranking
├── nlp/
│   ├── summarizer.py       Local extractive summarizer (short/medium/detailed) + LLM stub
│   ├── tasks.py            Action items, deadlines, entities, risks extraction
│   └── compare.py          Two-document comparison
├── email_connectors/
│   ├── base.py             EmailConnector interface
│   ├── mock_connector.py   MOCK: reads sample_data/emails/*.json (clearly labelled)
│   ├── gmail_stub.py       NOT CONFIGURED stub with real-integration notes
│   └── digest.py           Daily briefing builder (urgent/action/meetings/follow-ups/noise)
├── voice/
│   ├── stt.py              STT abstraction (BrowserSTT bridge + MockSTT for tests)
│   └── tts.py              TTS abstraction (BrowserTTS bridge + MockTTS for tests)
├── policy/
│   ├── sensitivity.py      SAFE / SENSITIVE / BLOCKED classifier (regex + keyword rules)
│   ├── redaction.py        Replaces sensitive spans with [REDACTED:*] before any NLP
│   └── engine.py           Allowlist/denylist checks; action risk policy; single choke point
├── memory/manager.py       Session vs persistent memory; encrypted at rest; review/delete/toggle
├── audit/logger.py         Append-only audit log of every access, block, and action
└── persona/engine.py       Personality layer: tone, wit budget, hard guardrails
frontend/src/               React UI (no component library; hand-built design system)
config/                     settings.yaml, policy.yaml, personality.yaml
sample_data/                Approved workspace docs, a non-approved "private_vault", mock inbox
backend/tests/              pytest suite (see §6)
```

Rule of dependency direction: `orchestrator` may call everything below it; `policy`,
`persona`, `nlp`, `files`, `email_connectors` never import each other's internals and never
import the orchestrator. **All content passes through `policy` before it reaches `nlp` or
any response.**

## 3. Privacy model and permission rules

- **Least privilege**: the indexer can only see folders listed in `settings.yaml →
  approved_folders`. Everything else on disk does not exist to MAYA. Denylist patterns
  (`private`, `.ssh`, `wallet`, …) are pruned even inside approved folders.
- **Classification**: every document and email is classified `SAFE / SENSITIVE / BLOCKED`
  before use.
  - `BLOCKED` (banking, payment apps, brokerage/demat, tax, payroll, passwords, OTPs,
    security answers, government IDs, card/account numbers, financial statements): content
    is never summarized, never stored, never shown — only a category-level notice
    ("1 banking email shielded").
  - `SENSITIVE` (health, legal, identity-adjacent): summarized only with redaction applied,
    flagged in the UI, and **the personality layer disables all humor**.
  - `SAFE`: summarized normally, still passed through token-level redaction (a stray card
    number in a safe doc still gets masked).
- **Redaction before NLP**: the summarizer only ever receives redacted text.
- **Confirmation gates**: read/search/summarize/draft are allowed. Move, delete
  (→ reversible `.maya_trash`), send-email (mock outbox), and any external side effect
  create a *pending action* showing the exact operation; nothing executes until the user
  approves it (button or spoken "confirm"). Pending actions expire.
- **Audit log**: every file read, email access, classification block, memory write, and
  executed/cancelled action is logged to SQLite and visible in the UI. Every assistant
  answer lists the sources it touched.
- **Memory**: persistent memory only via explicit "remember …" or settings; session memory
  dies with the session; memory values are Fernet-encrypted at rest (key in `data/`,
  0600 — a production build would use the OS keychain); values that classify as BLOCKED
  are refused; memory can be toggled off entirely, reviewed, and deleted.
- **No raw retention**: email bodies are read from the connector on demand; digests store
  only redacted summaries in the session, not raw bodies.

## 4. Personality plan

`config/personality.yaml` holds identity, tone rules, quip pools per context, Telugu flair
phrases, and hard guardrails. `persona/engine.py` enforces: helpful first, witty second; a
wit *budget* (at most ~1 in 3 responses gets a quip, never twice in a row, no repeats from
the last 6); **zero humor** when context is SENSITIVE/BLOCKED or topic-matched (health,
money, identity, grief, legal); no flirting/meanness by construction (quips come only from
the reviewed pools). Wit level (off/subtle/classic) is user-configurable in Settings.

## 5. Voice plan

- Browser `SpeechRecognition` for STT (Chrome/Edge); push-to-talk always works; optional
  wake-phrase mode ("Maya …") when continuous listening is enabled.
- Browser `speechSynthesis` for TTS with voice/rate settings; speaking is interruptible —
  starting to talk (or pressing the orb) cancels playback.
- The backend never receives audio — only final transcripts (privacy: audio stays local).
- `voice/stt.py`/`tts.py` define the abstraction + mocks so the pipeline is testable and a
  local engine (whisper.cpp / Piper) can be plugged in later.
- Risky voice commands route through the same confirmation gate; "confirm" / "cancel" are
  recognized as gate responses.

## 6. Test plan (pytest, written alongside each module)

1. `test_file_search.py` — indexing approved folders only; keyword/type/folder/date search;
   the non-approved `private_vault` is never indexed.
2. `test_summarization.py` — short/medium/detailed modes; action items/deadlines/risks;
   blocked docs are refused.
3. `test_sensitivity.py` — classifier on OTPs, card numbers (Luhn), PAN/Aadhaar, payroll,
   banking senders, health, safe text.
4. `test_redaction.py` — sensitive spans masked; no raw secrets survive redaction.
5. `test_confirmation.py` — risky actions don't execute without approval; approve executes;
   cancel doesn't; everything audited.
6. `test_intents.py` — voice/chat command parsing, wake-phrase stripping, slots,
   clarification questions.
7. `test_email_digest.py` — digest buckets; blocked emails shielded (no content leaks).
8. `test_memory.py` — store/list/delete; blocked values refused; toggle off.
9. `test_api.py` — end-to-end via FastAPI TestClient: chat → pending action → confirm.
10. `test_persona.py` — no humor in sensitive contexts; wit budget respected.

## 7. Assumptions

1. No LLM API key is available: summarization is **extractive** (sentence scoring), which
   is honest, deterministic, and testable. `nlp/summarizer.py` exposes an `LLMSummarizer`
   stub showing exactly where an API-backed model would plug in.
2. Email is **mock data only** (no OAuth in this environment). The Gmail connector stub
   documents the real integration path. The UI labels the inbox "Mock data".
3. Voice depends on browser support (Chrome/Edge have Web Speech API; Firefox lacks STT).
   Typed chat is always available — voice-first, not voice-only.
4. Single local user; no auth layer. The server binds to localhost.
5. "Desktop app" is satisfied by a local web app per the brief's explicit allowance.
6. Sample workspace and inbox are fictional but realistic (Indian business context:
   logistics SOPs, vendor reviews, festival campaign planning).

## 8. Build order

configs + sample data → policy engine (+tests) → files/nlp (+tests) → email digest
(+tests) → memory/audit (+tests) → persona (+tests) → orchestrator/actions/intents
(+tests) → FastAPI app (+tests) → frontend design system → frontend views → run + verify
(curl + headless screenshot) → docs (README/ARCHITECTURE/SETUP/demo) → final validation.
