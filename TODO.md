# MAYA — Build TODO

Working checklist. `[x]` = done and verified, `[~]` = in progress, `[ ]` = not started.

## Foundations
- [x] Implementation plan (PLAN.md)
- [x] Config files: settings.yaml, policy.yaml, personality.yaml
- [x] Sample data: workspace docs, private_vault (non-approved), mock inbox

## Backend
- [x] db.py — SQLite helper
- [x] policy/sensitivity.py — SAFE/SENSITIVE/BLOCKED classifier
- [x] policy/redaction.py — redaction layer
- [x] policy/engine.py — allowlist/denylist + action risk policy
- [x] files/parsers.py — TXT/MD/CSV/PDF/DOCX extraction
- [x] files/indexer.py — approved-folders index (blocked files: metadata only)
- [x] files/search.py — search + filters + latest-ranking
- [x] nlp/summarizer.py — extractive summarizer + LLM stub (not configured)
- [x] nlp/tasks.py — action items / deadlines / entities / risks
- [x] nlp/compare.py — document comparison
- [x] email_connectors/ — base, mock (labelled), gmail stub, digest builder
- [x] voice/ — STT/TTS abstractions + mocks (browser does the real work)
- [x] memory/manager.py — encrypted memory, blocked-value refusal, toggle
- [x] audit/logger.py — append-only audit log
- [x] persona/engine.py — personality + enforced guardrails
- [x] orchestrator/intents.py — command parser
- [x] orchestrator/actions.py — confirmation gate (reversible delete, simulated send)
- [x] orchestrator/orchestrator.py — routing + session context
- [x] app.py — FastAPI routes + static serving

## Tests — 91 passing
- [x] test_sensitivity.py · test_redaction.py · test_file_search.py
- [x] test_summarization.py · test_email_digest.py · test_memory.py
- [x] test_persona.py · test_intents.py · test_confirmation.py · test_api.py

## Frontend
- [x] Design system (jewel-tone dark, Fraunces/Manrope vendored, motion)
- [x] Orb with idle/listening/thinking/speaking states + waveform
- [x] Command center (chat stream, cards, composer, mic, wake & speak toggles)
- [x] Right rail: glance stats, approved sources, activity feed
- [x] Files view (search/filters, summarize modes, two-file compare)
- [x] Inbox view (digest buckets, shielded panel, draft reply → gated send)
- [x] Memory view, Audit view, Settings view
- [x] Action confirmation drawer (exact operation, approve/cancel, expiry)
- [x] Build + served from FastAPI at :8930

## Verification & docs
- [x] Full test suite green (91 passed)
- [x] Server boot + curl smoke checks (meta, sources, chat, digest, blocked refusal)
- [x] Headless-browser screenshots of 8 UI states (docs/screenshots/)
- [x] Confirmation gates validated end-to-end (cancel + approve paths, audit entries)
- [x] Blocked-content shielding validated (no OTP/salary/card leaks in API output)
- [x] Voice command routing validated (intent tests + four canonical commands)
- [x] README.md, ARCHITECTURE.md, SETUP.md
- [x] demo/demo_script.md + scripts/demo.py (ran clean end-to-end)
- [x] Final commit + push

## Deliberately not done (honest scope)
- [ ] Real Gmail OAuth connector (documented stub only)
- [ ] LLM-backed abstractive summarization (documented seam only)
- [ ] PPTX indexing · local STT/TTS engines · OS-keychain key storage
