# MAYA — Setup Guide

## Prerequisites

- Python **3.11+**
- Node **18+** (only to build the frontend once)
- For voice: Chrome or Edge (Web Speech API). Firefox lacks speech recognition —
  typed chat still works fully.

## Install & run

```bash
git clone <this repo> && cd MAYA

# Backend deps in a venv
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# Frontend build (FastAPI serves frontend/dist)
cd frontend
npm install
npm run build
cd ..

# Run MAYA
.venv/bin/python backend/run.py
```

Open **http://127.0.0.1:8930**. The workspace is pre-configured to index
`sample_data/workspace` (a fictional logistics business) and the mock inbox, so every
feature is demonstrable immediately.

## Tests

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Frontend development mode (optional)

```bash
.venv/bin/python backend/run.py          # terminal 1 — API on :8930
cd frontend && npm run dev               # terminal 2 — Vite on :5173 (proxies /api)
```

## Pointing MAYA at your own folders

Edit `config/settings.yaml`:

```yaml
workspace:
  approved_folders:
    - /home/you/Documents/work        # absolute, or relative to the repo root
```

Restart, or hit `POST /api/index/rebuild`. Deny patterns (`private`, `.ssh`, …) are
pruned even inside approved folders. Supported types: `.txt .md csv .pdf .docx`.

## Voice notes

- **Push-to-talk**: click the mic, speak, it submits on pause.
- **Wake mode**: toggle "wake phrase" under the composer, then say “Maya, …”. The mic
  stays open in your browser (indicated by the orb + toggle); utterances without the
  wake word are discarded client-side.
- **Spoken replies**: toggle "spoken replies"; pick voice/rate in Settings. en-IN
  voices fit MAYA best when your OS has them.
- Audio never reaches the backend — recognition and synthesis are in-browser.

## Enabling a real email connector (not included)

`config/settings.yaml → email.provider: gmail` activates the stub, which refuses to
run without credentials. To actually implement it, follow the notes in
`backend/maya/email_connectors/gmail_stub.py` (official Gmail API, `gmail.readonly`
scope, approved labels only) — the policy pipeline needs no changes.

## Plugging in an LLM summarizer (optional, not included)

`backend/maya/nlp/summarizer.py` defines `LLMSummarizer` as the seam: implement the
client call, set `MAYA_LLM_API_KEY`, and return it from `get_summarizer()`. Redaction
still happens before any text would reach it.

## Troubleshooting

- **Port busy** — change `server.port` in `config/settings.yaml`.
- **Blank page** — you skipped `npm run build`; FastAPI serves `frontend/dist`.
- **Mic button disabled** — browser lacks Web Speech API (use Chrome/Edge).
- **Reset state** — delete `data/` (DB, memory key, trash, outbox regenerate).
