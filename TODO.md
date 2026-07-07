# MAYA — Build TODO

Working checklist. `[x]` = done and verified, `[~]` = in progress, `[ ]` = not started.

## Foundations
- [x] Implementation plan (PLAN.md)
- [~] Config files: settings.yaml, policy.yaml, personality.yaml
- [ ] Sample data: workspace docs, private_vault (non-approved), mock inbox

## Backend
- [ ] db.py — SQLite helper
- [ ] policy/sensitivity.py — SAFE/SENSITIVE/BLOCKED classifier
- [ ] policy/redaction.py — redaction layer
- [ ] policy/engine.py — allowlist/denylist + action risk policy
- [ ] files/parsers.py — TXT/MD/CSV/PDF/DOCX extraction
- [ ] files/indexer.py — approved-folders index
- [ ] files/search.py — search + filters + ranking
- [ ] nlp/summarizer.py — extractive summarizer + LLM stub
- [ ] nlp/tasks.py — action items / deadlines / entities / risks
- [ ] nlp/compare.py — document comparison
- [ ] email_connectors/ — base, mock (labelled), gmail stub, digest builder
- [ ] voice/ — STT/TTS abstractions + mocks
- [ ] memory/manager.py — encrypted memory, session vs persistent, toggle
- [ ] audit/logger.py — audit log
- [ ] persona/engine.py — personality + guardrails
- [ ] orchestrator/intents.py — command parser
- [ ] orchestrator/actions.py — confirmation gate
- [ ] orchestrator/orchestrator.py — routing + session context
- [ ] app.py — FastAPI routes + static serving

## Tests
- [ ] test_sensitivity.py
- [ ] test_redaction.py
- [ ] test_file_search.py
- [ ] test_summarization.py
- [ ] test_email_digest.py
- [ ] test_memory.py
- [ ] test_persona.py
- [ ] test_intents.py
- [ ] test_confirmation.py
- [ ] test_api.py

## Frontend
- [ ] Design system (palette, type, motion) + vendored fonts
- [ ] Orb with idle/listening/thinking/speaking states
- [ ] Command center (chat stream, composer, voice controls)
- [ ] Briefing panel + task queue + privacy shield
- [ ] Files view (search, summarize, compare)
- [ ] Inbox view (digest buckets, shielded notices)
- [ ] Memory view, Audit view, Settings view
- [ ] Action confirmation drawer
- [ ] Build + serve from FastAPI

## Verification & docs
- [ ] Run full test suite
- [ ] Boot server, curl API smoke checks
- [ ] Headless browser screenshot of UI states
- [ ] Validate confirmation gates end-to-end
- [ ] Validate blocked-content shielding end-to-end
- [ ] README.md, ARCHITECTURE.md, SETUP.md
- [ ] demo/demo_script.md + scripts/demo.py
- [ ] Final commit + push
