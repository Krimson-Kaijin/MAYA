# MAYA — Demo Script (≈5 minutes)

A realistic morning with Ravi Teja, operations lead at Dhruva Freight (the fictional
sample workspace). Run `.venv/bin/python backend/run.py`, open http://127.0.0.1:8930.
Every step below works with typed input; in Chrome/Edge you can speak any of these
with the mic or wake mode ("Maya, …") instead.

---

**1 · The briefing.**
Type (or say): **“Maya, what should I prioritize today?”**
MAYA builds the day from the mock inbox + recent docs: suggested next actions (the
Meridian escalation first), urgent email, meetings, action items from Monday's ops
sync, recent files. Note the *accessed* chips under the reply — exactly what she
touched — and the right-rail glance panel updating.

**2 · Email, with the shield up.**
**“Summarize today's important emails.”**
The digest buckets 12 messages: urgent (Meridian escalation, the CEO's board request),
needing action, meetings, noise. At the bottom, the rose panel: **3 messages shielded**
— a bank OTP, a payslip, a card statement — classified at category level, content
never read. The OTP code appears nowhere in the UI, ever.

**3 · Files, versions, comparison.**
**“Find the latest logistics SOP.”** → v3 ranks first.
**“Compare these two files.”** → side-by-side summaries; MAYA notices they're versions
of the same document and which is newer (booking cut-off moved 14:00→15:00, doc
turnaround 24h→12h show up in the distinct-terms chips).
**“Summarize the first one in detail.”** → detailed mode with action items, deadlines,
entities and risks extracted.

**4 · The refusal (the point of the whole thing).**
**“Summarize the bank statement.”**
It sits *inside* the approved folder — and MAYA still declines, plainly and without
humor: banking/payment-card/payroll content stays shielded. Check **Audit trail**:
the refusal is logged with `outcome: refused`.

**5 · A gated action, both ways.**
**“Delete the festival campaign ideas.”**
The confirmation drawer rises with the exact operation
(`delete_file({"path": …}）`— reversible, to `data/trash/`). Click **Cancel** (or say
“cancel”): nothing changes. Ask again, then **Approve** (or say “confirm”): the file
moves to trash, the reply says exactly what happened, and both request and execution
are in the audit trail.

**6 · Drafting without sending.**
Open **Inbox**, click **Draft reply** on Priya's escalation. A template draft appears —
clearly marked *draft — not sent*. Clicking **Send (asks confirmation)** raises the
drawer; even approval only writes to a simulated outbox (`data/outbox.json`) — this
prototype never transmits mail.

**7 · Memory that minds its manners.**
**“Remember that I prefer short summaries before 10am.”** → stored (encrypted at rest).
**“Remember my card number is 4539 1488 0343 6467.”** → refused: blocked category.
Open **Memory** to review/delete items or switch memory off entirely.

**8 · Personality, bounded.**
Ask for a few digests/searches in a row — MAYA is witty *sometimes* (never twice in a
row, never the same line). Now summarize `personal_reminder.md` (a doctor's
appointment): flagged **sensitive**, redacted, and delivered with zero humor.
Settings → wit level **off** silences the quips entirely.

**9 · Voice round-trip (Chrome/Edge).**
Toggle **wake phrase**, say **“Maya, find the vendor review.”** The orb switches to
listening (waveform), thinking (violet spin), then speaking (gold pulse) if spoken
replies are on. Start talking mid-reply — she stops (interruption handling). The
composer footnote is accurate: audio stays in the browser; the backend sees text only.
