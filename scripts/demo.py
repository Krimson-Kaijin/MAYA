"""Scripted CLI demo of MAYA's core flows — no browser needed.

Run:  .venv/bin/python scripts/demo.py

Drives the same orchestrator the UI uses, against the repo's sample data, with an
in-memory database. The gated-delete step targets a scratch file this script creates,
so the sample workspace is left exactly as it was.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from maya.audit import AuditLogger                    # noqa: E402
from maya.config import Config                        # noqa: E402
from maya.db import Database                          # noqa: E402
from maya.email_connectors import get_connector       # noqa: E402
from maya.files import FileIndexer                    # noqa: E402
from maya.memory import MemoryManager                 # noqa: E402
from maya.orchestrator import ActionGate, Orchestrator  # noqa: E402
from maya.persona import Persona                      # noqa: E402
from maya.policy import PolicyEngine                  # noqa: E402

GOLD, TEAL, ROSE, DIM, END = "\033[33m", "\033[36m", "\033[31m", "\033[2m", "\033[0m"


def say(role: str, text: str) -> None:
    tag = f"{TEAL}you{END}" if role == "you" else f"{GOLD}maya{END}"
    body = textwrap.fill(text, width=92, subsequent_indent="       ")
    print(f"\n{tag} ▸ {body}")


def main() -> None:
    config = Config.load(REPO)
    db = Database(":memory:")
    audit = AuditLogger(db)
    policy = PolicyEngine(config)
    indexer = FileIndexer(config, db, policy, audit)
    stats = indexer.rebuild()
    gate = ActionGate(policy, audit, config, on_files_changed=indexer.rebuild)
    maya = Orchestrator(
        config=config, db=db, policy=policy, indexer=indexer,
        connector=get_connector(config),
        memory=MemoryManager(db, config, policy.classifier, audit),
        audit=audit, persona=Persona(config.personality, wit_level="classic"),
        gate=gate,
    )
    print(f"{DIM}— MAYA demo · indexed {stats.indexed} files, "
          f"{stats.blocked} blocked (metadata only) —{END}")

    def ask(text: str) -> dict:
        say("you", text)
        r = maya.handle(text, session_id="demo")
        say("maya", r["reply"])
        return r

    # 1 · briefing
    ask("Maya, what should I prioritize today?")

    # 2 · email digest with shielding
    r = ask("Maya, summarize today's important emails.")
    shielded = r["cards"][0]["counts"]["shielded"]
    print(f"{DIM}   [shielded bucket: {shielded} messages — content never read]{END}")

    # 3 · files: find latest, compare, summarize
    ask("Maya, find the latest logistics SOP.")
    ask("Compare these two files.")
    ask("Summarize the first one briefly.")

    # 4 · the refusal
    r = ask("Summarize the bank statement.")
    assert r["privacy"]["level"] == "BLOCKED"
    print(f"{DIM}   [refused — categories: {', '.join(r['privacy']['categories'])}]{END}")

    # 5 · gated delete on a scratch file (cancel, then confirm)
    scratch = config.approved_folders[0] / "notes" / "demo_scratch.txt"
    scratch.write_text("Temporary file created by scripts/demo.py to demonstrate "
                       "the confirmation gate.\n")
    indexer.rebuild()
    ask("Delete the demo scratch file.")
    ask("Cancel.")
    print(f"{DIM}   [file still exists: {scratch.exists()}]{END}")
    ask("Delete the demo scratch file.")
    ask("Confirm.")
    print(f"{DIM}   [file still exists: {scratch.exists()} — moved to data/trash/]{END}")

    # 6 · memory: store, refuse blocked, review
    ask("Remember that I prefer short summaries before 10am.")
    ask("Remember my card number is 4539 1488 0343 6467.")
    ask("What do you know about me?")

    # 7 · audit tail
    print(f"\n{DIM}— last 6 audit events —{END}")
    for e in audit.recent(limit=6):
        colour = ROSE if e["outcome"] in ("refused", "shielded") else TEAL
        print(f"  {DIM}{e['ts'][11:19]}{END} {colour}{e['event']:<18}{END} "
              f"{e['target'][:40]:<40} {e['outcome']}")

    print(f"\n{DIM}Demo complete. The sample workspace is unchanged "
          f"(scratch file is in data/trash/).{END}\n")


if __name__ == "__main__":
    main()
