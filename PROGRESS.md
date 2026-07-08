# MAYA — Progress Log

Newest entries at the bottom. Honest status only: nothing here is marked done unless it
was actually run/verified.

- **2026-07-07** · Repo initialized on branch `claude/maya-ai-assistant-prototype-1d8iw6`.
  Environment verified: Python 3.11.15, Node 22, all backend deps install cleanly in
  `.venv` (fastapi, uvicorn, pyyaml, pypdf, python-docx, cryptography, pytest, httpx).
  Google Fonts (Fraunces + Manrope) reachable for vendoring.
- **2026-07-07** · PLAN.md written: module boundaries, privacy model, test plan,
  assumptions, build order.
- **2026-07-07** · Configs written: settings.yaml (allowlists), policy.yaml (classifier +
  redaction + action risk), personality.yaml (tone, quip pools, guardrails).
- **2026-07-07** · Sample data written: Dhruva Freight workspace (SOP v2/v3, meeting
  notes, vendor review, CSV, campaign notes), a BLOCKED bank statement inside the
  approved folder, a SENSITIVE health note, a non-approved private_vault, and a 12-message
  mock inbox including OTP/payslip/card-statement messages for shielding demos.
- **2026-07-07** · Backend implemented: policy engine (classifier with Luhn/PAN/IFSC/
  Aadhaar/OTP detectors, redactor, action-risk table), file indexer + search, extractive
  summarizer + task/deadline/risk extraction + compare, mock email connector + digest
  builder with shielded bucket, gmail stub (not configured, documented), voice STT/TTS
  abstractions (browser-based, mocks for tests), encrypted memory manager, audit logger,
  persona engine with enforced wit budget, intent parser, action gate, orchestrator,
  FastAPI app.
- **2026-07-07** · Bugs found by tests and fixed: Aadhaar regex partially matched
  16-digit non-card numbers (added lookarounds); "yes, go ahead" and bare "find" were
  unparsed. **Test suite: 91 passed, 0 failed** (`.venv/bin/python -m pytest backend/tests`).
- **2026-07-07** · Frontend built: React + Vite, hand-rolled design system (ink dark +
  marigold/peacock/violet/rose jewel tones, Fraunces + Manrope vendored locally into
  frontend/public/fonts — no runtime network deps). Orb with 4 animated states, chat
  cards, briefing/files/inbox/memory/audit/settings views, confirmation drawer,
  privacy shield pill, activity feed. `npm run build` clean (47 modules).
- **2026-07-07** · Live verification against the running server (`:8930`): find →
  logistics_sop_v3 first; digest counts urgent 2 / action 3 / meetings 2 / noise 2 /
  shielded 3 with zero OTP leakage (asserted on raw JSON); bank-statement summarization
  refused with BLOCKED privacy payload. Fixed while verifying: refusal category list
  now comma-joined; meetings bucket no longer hijacks emails that merely mention
  meetings; "1 need action" grammar.
- **2026-07-07** · Headless-chromium UI verification (Playwright): 8 screenshots — orb
  glyph మ renders, digest shield panel with category chips, confirmation drawer shows
  exact `delete_file({...})` operation, files view badges (SAFE/SENSITIVE/BLOCKED),
  audit trail with shielded/cancelled outcomes. Zero console/page errors. Key shots
  copied to docs/screenshots/.
- **2026-07-07** · Docs written: README (features/mocks/privacy/limitations),
  ARCHITECTURE, SETUP, demo/demo_script.md. `scripts/demo.py` ran end-to-end clean
  (briefing → digest → compare → refusal → gated delete cancel+confirm → memory
  refusal → audit tail). Final suite: **91 passed**. Committed and pushed.
