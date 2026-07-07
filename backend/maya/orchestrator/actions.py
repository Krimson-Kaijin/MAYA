"""Action gate — confirmation for anything with side effects.

Risk comes from config/policy.yaml → actions:
  safe       runs immediately (read/search/summarize/draft…)
  gated      creates a PendingAction; NOTHING happens until the user approves
             the exact operation shown to them (button click or spoken confirm)
  forbidden  never available, refused outright

Gated executors in this prototype:
  move_file   — only between approved folders
  delete_file — reversible: moves the file to data/trash/, never unlinks
  send_email  — SIMULATED: appends to data/outbox.json (mock connector);
                clearly labelled, no real mail leaves the machine
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class PendingAction:
    id: str
    action_type: str
    params: dict
    description: str
    risk: str = "gated"
    status: str = "pending"          # pending | executed | cancelled | expired
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    result: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "action_type": self.action_type, "params": self.params,
            "description": self.description, "risk": self.risk, "status": self.status,
            "expires_in": max(0, int(self.expires_at - time.time())),
            "result": self.result,
        }


class ActionGate:
    def __init__(self, policy, audit, config, on_files_changed=None):
        self.policy = policy
        self.audit = audit
        self.config = config
        self.on_files_changed = on_files_changed
        self._pending: dict[str, PendingAction] = {}

    # -- lifecycle -----------------------------------------------------------------
    def submit(self, action_type: str, params: dict, description: str) -> dict:
        risk = self.policy.action_risk(action_type)
        if risk == "forbidden":
            self.audit.log("action.forbidden", target=action_type, outcome="refused")
            return {"status": "forbidden", "action_type": action_type}
        if risk == "safe":
            # Safe actions don't come through the gate in practice; keep it strict anyway.
            return {"status": "not_gated", "action_type": action_type}
        action = PendingAction(
            id=uuid.uuid4().hex[:10], action_type=action_type, params=params,
            description=description,
            expires_at=time.time() + self.policy.confirmation_timeout,
        )
        self._pending[action.id] = action
        self.audit.log("action.requested", target=action_type, detail=description)
        return {"status": "pending", "action": action.to_dict()}

    def _expire_stale(self) -> None:
        now = time.time()
        for a in self._pending.values():
            if a.status == "pending" and a.expires_at < now:
                a.status = "expired"
                self.audit.log("action.expired", target=a.action_type, detail=a.description)

    def pending(self) -> list[dict]:
        self._expire_stale()
        return [a.to_dict() for a in self._pending.values() if a.status == "pending"]

    def latest_pending_id(self) -> str | None:
        self._expire_stale()
        candidates = [a for a in self._pending.values() if a.status == "pending"]
        if not candidates:
            return None
        return max(candidates, key=lambda a: a.created_at).id

    def confirm(self, action_id: str, approve: bool) -> dict:
        self._expire_stale()
        action = self._pending.get(action_id)
        if action is None:
            return {"status": "not_found"}
        if action.status != "pending":
            return {"status": action.status, "action": action.to_dict()}
        if not approve:
            action.status = "cancelled"
            self.audit.log("action.cancelled", target=action.action_type,
                           detail=action.description, outcome="cancelled")
            return {"status": "cancelled", "action": action.to_dict()}
        try:
            action.result = self._execute(action)
            action.status = "executed"
            self.audit.log("action.executed", target=action.action_type,
                           detail=f"{action.description} → {action.result}")
        except Exception as exc:
            action.status = "cancelled"
            action.result = f"failed: {exc}"
            self.audit.log("action.failed", target=action.action_type,
                           detail=str(exc), outcome="error")
            return {"status": "failed", "action": action.to_dict(), "error": str(exc)}
        return {"status": "executed", "action": action.to_dict()}

    # -- executors ---------------------------------------------------------------------
    def _execute(self, action: PendingAction) -> str:
        if action.action_type == "move_file":
            return self._move_file(action.params)
        if action.action_type == "delete_file":
            return self._delete_file(action.params)
        if action.action_type == "send_email":
            return self._send_email(action.params)
        raise ValueError(f"No executor for action '{action.action_type}'")

    def _move_file(self, params: dict) -> str:
        src = Path(params["src"]).resolve()
        dest_dir = Path(params["dest_dir"]).resolve()
        if not self.policy.is_path_allowed(src):
            raise PermissionError(f"Source is outside approved folders: {src}")
        if not self.policy.is_path_allowed(dest_dir / "placeholder.txt"):
            raise PermissionError(f"Destination is outside approved folders: {dest_dir}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / src.name
        shutil.move(str(src), str(target))
        if self.on_files_changed:
            self.on_files_changed()
        return f"moved to {target}"

    def _delete_file(self, params: dict) -> str:
        src = Path(params["path"]).resolve()
        if not self.policy.is_path_allowed(src):
            raise PermissionError(f"Path is outside approved folders: {src}")
        trash = self.config.data_dir / "trash"
        trash.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        target = trash / f"{stamp}_{src.name}"
        shutil.move(str(src), str(target))
        if self.on_files_changed:
            self.on_files_changed()
        return f"moved to trash ({target.name}) — restorable from data/trash/"

    def _send_email(self, params: dict) -> str:
        # SIMULATED SEND — mock connector. The draft lands in data/outbox.json,
        # clearly marked; no real email is transmitted anywhere.
        outbox = self.config.data_dir / "outbox.json"
        entries = []
        if outbox.exists():
            entries = json.loads(outbox.read_text(encoding="utf-8"))
        entries.append({
            "to": params.get("to", ""), "subject": params.get("subject", ""),
            "body": params.get("body", ""),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "transport": "SIMULATED — mock connector, no real email sent",
        })
        outbox.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        return f"simulated send recorded in {outbox.name} (mock connector — nothing actually sent)"
