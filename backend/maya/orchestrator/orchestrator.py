"""Assistant orchestration: intent → skill → policy-checked result → persona reply.

Every handler returns a Response with:
  reply    — text shown in chat
  speak    — shorter line for TTS
  cards    — structured payloads the UI renders (digest, summary, files, …)
  pending_action — set when a gated action awaits confirmation
  accessed — exactly what MAYA touched to produce the result (transparency)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..email_connectors import build_digest
from ..files.search import search_index
from ..nlp import compare as nlp_compare
from ..nlp import tasks as nlp_tasks
from ..nlp.summarizer import ExtractiveSummarizer
from ..policy.sensitivity import SAFE
from .intents import parse_command

HELP_TEXT = (
    "Here's what I can do:\n"
    "• **Files** — \"find the latest logistics SOP\", \"summarize the vendor review in detail\", "
    "\"compare these two files\", \"extract action items from the ops sync notes\"\n"
    "• **Email** — \"summarize today's important emails\" (mock inbox in this prototype)\n"
    "• **Briefing** — \"what should I prioritize today?\"\n"
    "• **Memory** — \"remember that I prefer short summaries\", \"show memory\", \"forget …\"\n"
    "• **Reminders** — \"remind me to send the surge plan Friday\"\n"
    "• **Gated** — move/delete files and sending drafts always ask for confirmation first.\n"
    "Reading is free; anything with side effects shows you the exact action and waits."
)


@dataclass
class Response:
    reply: str = ""
    speak: str = ""
    intent: str = "unknown"
    cards: list[dict] = field(default_factory=list)
    pending_action: dict | None = None
    accessed: list[dict] = field(default_factory=list)
    privacy: dict | None = None

    def to_dict(self) -> dict:
        return {
            "reply": self.reply, "speak": self.speak or self.reply,
            "intent": self.intent, "cards": self.cards,
            "pending_action": self.pending_action, "accessed": self.accessed,
            "privacy": self.privacy,
        }


class Orchestrator:
    def __init__(self, *, config, db, policy, indexer, connector, memory, audit,
                 persona, gate, summarizer=None):
        self.config = config
        self.db = db
        self.policy = policy
        self.indexer = indexer
        self.connector = connector
        self.memory = memory
        self.audit = audit
        self.persona = persona
        self.gate = gate
        self.summarizer = summarizer or ExtractiveSummarizer()
        self._sessions: dict[str, dict] = {}

    # ------------------------------------------------------------------ session --
    def session(self, session_id: str) -> dict:
        return self._sessions.setdefault(session_id, {
            "last_hits": [], "last_digest_items": [], "last_doc": None,
        })

    # ------------------------------------------------------------------- entry --
    def handle(self, text: str, mode: str = "chat", session_id: str = "default") -> dict:
        intent = parse_command(text, self.config.wake_phrases)
        self.audit.log("command", target=intent.name, detail=f"mode={mode}")
        ctx = self.session(session_id)

        if intent.clarify:
            r = Response(reply=intent.clarify, speak=intent.clarify, intent=intent.name)
            return r.to_dict()

        handler = getattr(self, f"_do_{intent.name}", None)
        if handler is None:
            return self._do_unknown(intent, ctx).to_dict()
        return handler(intent, ctx).to_dict()

    # ------------------------------------------------------------- file helpers --
    def _resolve_doc(self, intent, ctx) -> tuple[dict | None, str | None]:
        """Find a document row from a query or an ordinal into the last results."""
        slots = intent.slots
        if "ordinal" in slots and slots["ordinal"] is not None:
            hits = ctx.get("last_hits") or []
            if not hits:
                return None, "I don't have recent results to refer to. Try a search first."
            idx = slots["ordinal"]
            idx = len(hits) - 1 if idx == -1 else idx - 1
            if idx < 0 or idx >= len(hits):
                return None, f"I only have {len(hits)} recent result(s)."
            path = hits[idx]
        else:
            query = slots.get("query", "")
            if not query:
                last = ctx.get("last_doc")
                if last:
                    path = last
                else:
                    return None, "Which document do you mean?"
            else:
                found = search_index(self.db, query, latest=True, limit=1)
                if not found:
                    return None, f"I couldn't find anything matching “{query}” in your approved folders."
                path = found[0].path
        row = self.indexer.get(path)
        if row is None:
            return None, "That file is no longer in the index."
        return dict(row), None

    @staticmethod
    def _file_card(hits: list) -> dict:
        return {"type": "files", "items": [h.to_dict() for h in hits]}

    # ------------------------------------------------------------------ intents --
    def _do_greeting(self, intent, ctx) -> Response:
        hour = datetime.now().hour
        text = self.persona.greeting(hour)
        return Response(reply=text, speak=text, intent="greeting")

    def _do_help(self, intent, ctx) -> Response:
        return Response(reply=HELP_TEXT, speak="I search and summarize your approved files, "
                        "digest your email, build your daily briefing, and always ask before "
                        "anything with side effects.", intent="help")

    def _do_unknown(self, intent, ctx) -> Response:
        reply = ("I didn't catch a task in that. Try “find …”, “summarize …”, "
                 "“summarize my emails”, or “what should I prioritize today?” — "
                 "or say “help” for the full list.")
        return Response(reply=reply, speak=reply, intent="unknown")

    # ---- files -------------------------------------------------------------------
    def _do_find_file(self, intent, ctx) -> Response:
        slots = intent.slots
        hits = search_index(
            self.db, slots.get("query", ""),
            ftype=slots.get("type"), latest=slots.get("latest", False), limit=6,
        )
        self.audit.log("files.search", detail=f"q='{slots.get('query','')}' hits={len(hits)}")
        if not hits:
            reply = (f"Nothing matching “{slots.get('query','')}” in your approved folders. "
                     f"I only see what you've allowed me to see.")
            return Response(reply=reply, speak=reply, intent="find_file")

        ctx["last_hits"] = [h.path for h in hits]
        ctx["last_doc"] = hits[0].path
        shielded = [h for h in hits if h.shielded]
        core = f"Found {len(hits)} file{'s' if len(hits) != 1 else ''} — “{hits[0].name}” is the best match."
        if shielded:
            core += (f" {len(shielded)} of them is financial content I can list but won't open, "
                     f"per your privacy policy.")
            reply = core  # no humor when the result set touches blocked material
        else:
            reply = self.persona.compose(core, pool="file_found")
        return Response(
            reply=reply, speak=reply, intent="find_file",
            cards=[self._file_card(hits)],
            accessed=[{"kind": "index", "label": "file index",
                       "note": f"query: {slots.get('query','')}"}],
        )

    def _do_summarize_file(self, intent, ctx) -> Response:
        row, err = self._resolve_doc(intent, ctx)
        if err:
            return Response(reply=err, speak=err, intent="summarize_file")
        return self._summarize_row(row, intent.slots.get("mode", "medium"), ctx)

    def summarize_path(self, path: str, mode: str = "medium",
                       session_id: str = "default") -> dict:
        """Direct-path entry used by the Files UI (bypasses chat parsing)."""
        row = self.indexer.get(path)
        if row is None:
            reply = "That file isn't in the index of approved folders."
            return Response(reply=reply, speak=reply, intent="summarize_file").to_dict()
        return self._summarize_row(dict(row), mode, self.session(session_id)).to_dict()

    def _summarize_row(self, row: dict, mode: str, ctx: dict) -> Response:
        name = row["name"]
        if row["sensitivity"] == "BLOCKED":
            cats = [c for c in (row["categories"] or "").split(",") if c]
            reply = self.persona.refusal(cats, what=f"“{name}”")
            self.audit.log("files.summarize", target=name, sensitivity="BLOCKED",
                           outcome="refused")
            return Response(reply=reply, speak=reply, intent="summarize_file",
                            privacy={"level": "BLOCKED", "categories": cats})

        text = row["text"] or ""
        summary = self.summarizer.summarize(text, mode)
        report = nlp_tasks.analyze(text)
        ctx["last_doc"] = row["path"]
        self.audit.log("files.summarize", target=name, sensitivity=row["sensitivity"])

        sensitive = row["sensitivity"] != SAFE
        core = f"Here's the {mode} summary of “{name}”."
        reply = core if sensitive else self.persona.compose(core, pool="summary_done")
        if sensitive:
            reply += " This document contains sensitive material, so I've kept it redacted and plain."
        card = {
            "type": "summary", "file": name, "path": row["path"], "mode": mode,
            "sensitivity": row["sensitivity"],
            "summary": summary.to_dict(), "tasks": report.to_dict(),
        }
        speak = f"{core} {summary.headline}." if summary.headline else core
        return Response(
            reply=reply, speak=speak, intent="summarize_file", cards=[card],
            accessed=[{"kind": "file", "label": name, "note": f"read + summarized ({mode})"}],
            privacy={"level": row["sensitivity"],
                     "categories": [c for c in (row["categories"] or "").split(",") if c]},
        )

    def compare_paths(self, a: str, b: str) -> dict:
        """Direct-path comparison used by the Files UI."""
        rows = []
        for p in (a, b):
            row = self.indexer.get(p)
            if row is None:
                reply = f"“{p}” isn't in the index of approved folders."
                return Response(reply=reply, speak=reply, intent="compare_files").to_dict()
            rows.append(dict(row))
        return self._compare_rows(rows).to_dict()

    def _do_compare_files(self, intent, ctx) -> Response:
        slots = intent.slots
        rows = []
        if slots.get("use_context"):
            hits = (ctx.get("last_hits") or [])[:2]
            if len(hits) < 2:
                reply = ("Tell me which two — for example “compare the logistics SOP v2 and v3”, "
                         "or run a search first and then say “compare the first two”.")
                return Response(reply=reply, speak=reply, intent="compare_files")
            rows = [dict(self.indexer.get(p)) for p in hits if self.indexer.get(p)]
        else:
            for key in ("a", "b"):
                found = search_index(self.db, slots.get(key, ""), latest=False, limit=1)
                if not found:
                    reply = f"I couldn't find “{slots.get(key, '')}” in your approved folders."
                    return Response(reply=reply, speak=reply, intent="compare_files")
                rows.append(dict(self.indexer.get(found[0].path)))
        return self._compare_rows(rows)

    def _compare_rows(self, rows: list[dict]) -> Response:
        for row in rows:
            if row["sensitivity"] == "BLOCKED":
                cats = [c for c in (row["categories"] or "").split(",") if c]
                reply = self.persona.refusal(cats, what=f"“{row['name']}”")
                return Response(reply=reply, speak=reply, intent="compare_files",
                                privacy={"level": "BLOCKED", "categories": cats})

        result = nlp_compare.compare_documents(
            rows[0]["name"], rows[0]["text"] or "", rows[1]["name"], rows[1]["text"] or "")
        self.audit.log("files.compare", target=f"{rows[0]['name']} vs {rows[1]['name']}")
        core = f"Compared “{rows[0]['name']}” with “{rows[1]['name']}”."
        if result.get("version_note"):
            core += f" {result['version_note']}"
        reply = self.persona.compose(core, pool="task_ack")
        return Response(
            reply=reply, speak=core, intent="compare_files",
            cards=[{"type": "compare", **result}],
            accessed=[{"kind": "file", "label": r["name"], "note": "read for comparison"}
                      for r in rows],
        )

    def _do_extract_tasks(self, intent, ctx) -> Response:
        row, err = self._resolve_doc(intent, ctx)
        if err:
            return Response(reply=err, speak=err, intent="extract_tasks")
        if row["sensitivity"] == "BLOCKED":
            cats = [c for c in (row["categories"] or "").split(",") if c]
            reply = self.persona.refusal(cats, what=f"“{row['name']}”")
            return Response(reply=reply, speak=reply, intent="extract_tasks")
        report = nlp_tasks.analyze(row["text"] or "")
        self.audit.log("files.tasks", target=row["name"])
        n = len(report.action_items)
        core = f"Pulled {n} action item{'s' if n != 1 else ''} from “{row['name']}”."
        reply = self.persona.compose(core, pool="task_ack",
                                     sensitivity=row["sensitivity"])
        return Response(
            reply=reply, speak=core, intent="extract_tasks",
            cards=[{"type": "tasks", "file": row["name"], **report.to_dict()}],
            accessed=[{"kind": "file", "label": row["name"], "note": "task extraction"}],
        )

    # ---- email ---------------------------------------------------------------------
    def _digest(self) -> dict:
        emails = self.connector.list_messages()
        return build_digest(emails, self.policy, self.config.vip_senders, audit=self.audit)

    def _do_email_digest(self, intent, ctx) -> Response:
        try:
            digest = self._digest()
        except Exception as exc:
            reply = f"The email connector isn't available: {exc}"
            return Response(reply=reply, speak=reply, intent="email_digest")

        counts = digest["counts"]
        visible = [it for bucket in ("urgent", "action", "meetings", "follow_ups")
                   for it in digest["buckets"][bucket]]
        ctx["last_digest_items"] = visible

        core = (f"Inbox digest ready: {counts['urgent']} urgent, {counts['action']} needing "
                f"action, {counts['meetings']} meeting-related, {counts['follow_ups']} "
                f"follow-ups, {counts['noise']} noise.")
        reply = self.persona.compose(core, pool="inbox_summarized")
        shielded = digest["buckets"]["shielded"]
        if shielded:
            cats = sorted({c for it in shielded for c in it["categories"]})
            reply += " " + self.persona.shielded_note(len(shielded), cats)
        top = digest["buckets"]["urgent"][:1]
        speak = core + (f" Top urgent: {top[0]['sender_name']} — {top[0]['subject']}." if top else "")
        return Response(
            reply=reply, speak=speak, intent="email_digest",
            cards=[{"type": "digest", **digest}],
            accessed=[{"kind": "email", "label": f"{sum(counts.values())} messages via mock inbox",
                       "note": f"{len(shielded)} shielded unread"}],
        )

    def _do_draft_reply(self, intent, ctx) -> Response:
        items = ctx.get("last_digest_items") or []
        if not items:
            try:
                self._do_email_digest(parse_command("summarize my emails"), ctx)
                items = ctx.get("last_digest_items") or []
            except Exception:
                items = []
        if not items:
            reply = "I don't have a readable email to reply to yet — ask for the digest first."
            return Response(reply=reply, speak=reply, intent="draft_reply")

        target = None
        if "ordinal" in intent.slots:
            idx = intent.slots["ordinal"]
            idx = len(items) - 1 if idx == -1 else idx - 1
            if 0 <= idx < len(items):
                target = items[idx]
        elif "query" in intent.slots:
            q = intent.slots["query"].lower()
            for it in items:
                if q in it["sender_name"].lower() or q in it["subject"].lower():
                    target = it
                    break
        if target is None:
            target = items[0]

        first_name = (target["sender_name"].split() or ["there"])[0]
        body = (
            f"Hi {first_name},\n\n"
            f"Thanks for your note on “{target['subject']}”. I've gone through it and will "
            f"come back with specifics shortly.\n\n"
            f"— [Add your key points here]\n\n"
            f"Regards,\nRavi"
        )
        self.audit.log("email.draft", target=target["id"])
        core = (f"Draft ready for {target['sender_name']} — it stays a draft until you "
                f"explicitly send it, and sending will ask for confirmation.")
        card = {"type": "draft", "to": target["sender_name"], "email_id": target["id"],
                "subject": f"Re: {target['subject']}", "body": body,
                "note": "Template draft — review before sending. Send is gated + simulated (mock connector)."}
        return Response(reply=core, speak=core, intent="draft_reply", cards=[card],
                        accessed=[{"kind": "email", "label": target["subject"],
                                   "note": "read to draft reply"}])

    # ---- briefing --------------------------------------------------------------------
    def _do_briefing(self, intent, ctx) -> Response:
        accessed = []
        try:
            digest = self._digest()
            accessed.append({"kind": "email", "label": "mock inbox", "note": "digest built"})
        except Exception:
            digest = {"buckets": {k: [] for k in
                      ("urgent", "action", "meetings", "follow_ups", "noise", "shielded")},
                      "counts": {}}
        ctx["last_digest_items"] = [it for b in ("urgent", "action", "meetings", "follow_ups")
                                    for it in digest["buckets"][b]]

        # Most recent meeting notes → action items
        notes_hits = search_index(self.db, "meeting sync notes", latest=True, limit=1)
        doc_tasks, doc_name = [], None
        if notes_hits and not notes_hits[0].shielded:
            row = self.indexer.get(notes_hits[0].path)
            if row:
                doc_name = row["name"]
                doc_tasks = nlp_tasks.extract_action_items(row["text"] or "", limit=6)
                accessed.append({"kind": "file", "label": doc_name, "note": "action items"})

        recent_rows = self.db.query(
            "SELECT name, path, folder, mtime, sensitivity FROM file_index "
            "ORDER BY mtime DESC, name_date DESC LIMIT 5")
        recent = [dict(r) for r in recent_rows]

        reminders = [m for m in self.memory.list() if m["source"] == "reminder"] \
            if self.memory.enabled else []

        suggestions: list[str] = []
        for it in digest["buckets"]["urgent"][:2]:
            suggestions.append(f"Reply to {it['sender_name']}: “{it['subject']}”")
        for t in doc_tasks[:3]:
            suggestions.append(t if len(t) < 90 else t[:87] + "…")
        for it in digest["buckets"]["meetings"][:1]:
            suggestions.append(f"Prep for: {it['subject']}")
        suggestions = suggestions[:5]

        n_urgent = len(digest["buckets"]["urgent"])
        core = (f"Your briefing: {n_urgent} urgent email{'s' if n_urgent != 1 else ''}, "
                f"{len(digest['buckets']['meetings'])} meeting item(s), "
                f"{len(doc_tasks)} open action items from {doc_name or 'recent notes'}"
                f"{', ' + str(len(reminders)) + ' reminder(s)' if reminders else ''}.")
        reply = self.persona.compose(core, pool="briefing")
        shielded = digest["buckets"]["shielded"]
        if shielded:
            cats = sorted({c for it in shielded for c in it["categories"]})
            reply += " " + self.persona.shielded_note(len(shielded), cats)

        card = {
            "type": "briefing",
            "urgent": digest["buckets"]["urgent"],
            "action_emails": digest["buckets"]["action"],
            "meetings": digest["buckets"]["meetings"],
            "doc_tasks": {"file": doc_name, "items": doc_tasks},
            "recent_files": recent,
            "reminders": reminders,
            "suggestions": suggestions,
            "shielded_count": len(shielded),
        }
        speak = core + (f" First: {suggestions[0]}." if suggestions else "")
        return Response(reply=reply, speak=speak, intent="briefing",
                        cards=[card], accessed=accessed)

    # ---- memory ---------------------------------------------------------------------
    def _do_remember(self, intent, ctx) -> Response:
        return self._store_memory(intent.slots.get("value", ""), source="chat")

    def _do_remind(self, intent, ctx) -> Response:
        return self._store_memory(intent.slots.get("value", ""), source="reminder")

    def _store_memory(self, value: str, source: str) -> Response:
        outcome = self.memory.remember(value, source=source)
        if outcome.get("stored"):
            noun = "reminder" if source == "reminder" else "memory"
            core = f"{self.persona.ack()} Saved as a {noun} — you can review or delete it anytime in Memory."
            return Response(reply=core, speak=core, intent="remember")
        if outcome.get("reason") == "memory_disabled":
            reply = "Memory is switched off, so I didn't store that. You can enable it in Settings."
        else:
            reply = self.persona.refusal(outcome.get("categories", []),
                                         what="that detail")
            reply += " I don't keep financial or credential information in memory."
        return Response(reply=reply, speak=reply, intent="remember",
                        privacy={"level": "BLOCKED",
                                 "categories": outcome.get("categories", [])}
                        if outcome.get("reason") == "blocked_content" else None)

    def _do_memory_show(self, intent, ctx) -> Response:
        items = self.memory.list()
        core = (f"I'm holding {len(items)} memory item{'s' if len(items) != 1 else ''}. "
                f"All of them are yours to edit or delete.") if items else \
            "My memory about you is empty — I only store what you explicitly ask me to."
        return Response(reply=core, speak=core, intent="memory_show",
                        cards=[{"type": "memory", "items": items,
                                "enabled": self.memory.enabled}])

    def _do_memory_forget(self, intent, ctx) -> Response:
        q = intent.slots.get("query", "").lower()
        removed = 0
        for item in self.memory.list():
            if q and (q in item["value"].lower() or q in item["key"].lower()):
                self.memory.delete(item["id"])
                removed += 1
        reply = (f"Forgotten — removed {removed} matching item{'s' if removed != 1 else ''}."
                 if removed else f"Nothing in memory matches “{q}”.")
        return Response(reply=reply, speak=reply, intent="memory_forget")

    # ---- gated actions -----------------------------------------------------------------
    def _do_move_file(self, intent, ctx) -> Response:
        hits = search_index(self.db, intent.slots.get("query", ""), limit=1)
        if not hits:
            reply = f"I couldn't find “{intent.slots.get('query','')}” to move."
            return Response(reply=reply, speak=reply, intent="move_file")
        src = Path(hits[0].path)
        dest_name = intent.slots.get("dest", "").strip()
        root = self.config.approved_folders[0]
        dest_dir = (root / dest_name).resolve()
        desc = f"Move “{src.name}” → {dest_name}/ (inside your approved workspace)"
        outcome = self.gate.submit("move_file",
                                   {"src": str(src), "dest_dir": str(dest_dir)}, desc)
        return self._gate_response(outcome, "move_file")

    def _do_delete_file(self, intent, ctx) -> Response:
        row, err = self._resolve_doc(intent, ctx)
        if err:
            return Response(reply=err, speak=err, intent="delete_file")
        desc = (f"Delete “{row['name']}” — it will move to data/trash/ (reversible), "
                f"not be permanently erased")
        outcome = self.gate.submit("delete_file", {"path": row["path"]}, desc)
        return self._gate_response(outcome, "delete_file")

    def _gate_response(self, outcome: dict, intent_name: str) -> Response:
        if outcome["status"] == "forbidden":
            reply = "That action is on the forbidden list — I can't do it, by design."
            return Response(reply=reply, speak=reply, intent=intent_name)
        action = outcome.get("action", {})
        reply = (f"Ready, but I need your confirmation first: {action.get('description','')}. "
                 f"Say “confirm” or “cancel”, or use the buttons.")
        return Response(reply=reply, speak=reply, intent=intent_name,
                        pending_action=action)

    def _do_confirm(self, intent, ctx) -> Response:
        return self._resolve_gate(True)

    def _do_cancel(self, intent, ctx) -> Response:
        return self._resolve_gate(False)

    def _resolve_gate(self, approve: bool) -> Response:
        action_id = self.gate.latest_pending_id()
        if action_id is None:
            reply = ("There's nothing waiting for confirmation." if approve else
                     "Nothing to cancel — no action was pending.")
            return Response(reply=reply, speak=reply, intent="confirm")
        outcome = self.gate.confirm(action_id, approve)
        action = outcome.get("action", {})
        if outcome["status"] == "executed":
            reply = f"{self.persona.ack()} {action.get('description','')} — {action.get('result','')}."
        elif outcome["status"] == "failed":
            reply = f"That didn't work: {outcome.get('error','unknown error')}."
        else:
            reply = "Cancelled — nothing was changed."
        return Response(reply=reply, speak=reply, intent="confirm",
                        pending_action=action or None)
