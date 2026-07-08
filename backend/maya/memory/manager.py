"""Persistent memory for MAYA.

Rules (enforced here, not just documented):
  - Writes happen ONLY on explicit request ("remember that …") or via Settings.
  - Values that classify as BLOCKED (card numbers, OTPs, IDs, payroll…) are
    refused — MAYA will not remember them even if asked.
  - Values are Fernet-encrypted at rest; the key lives in data/maya.key (0600).
    A production build would use the OS keychain — noted honestly in README.
  - Memory can be reviewed, deleted item-by-item, cleared, or disabled entirely.

Session memory (conversation context like "the second file") lives in the
orchestrator's per-session dict and dies with the process — it is never written
to disk.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet

from ..policy.sensitivity import BLOCKED


class MemoryManager:
    def __init__(self, db, config, classifier, audit):
        self.db = db
        self.config = config
        self.classifier = classifier
        self.audit = audit
        self._fernet = self._load_fernet(config.data_dir) if config.get(
            "memory.encrypt_at_rest", True) else None

    @staticmethod
    def _load_fernet(data_dir: Path) -> Fernet:
        key_path = data_dir / "maya.key"
        if not key_path.exists():
            key_path.write_bytes(Fernet.generate_key())
            os.chmod(key_path, 0o600)
        return Fernet(key_path.read_bytes())

    # -- enabled toggle ---------------------------------------------------------
    @property
    def enabled(self) -> bool:
        override = self.db.kv_get("memory_enabled")
        if override is not None:
            return override == "1"
        return bool(self.config.get("memory.enabled", True))

    def set_enabled(self, value: bool) -> None:
        self.db.kv_set("memory_enabled", "1" if value else "0")
        self.audit.log("memory.toggle", detail=f"enabled={value}")

    # -- crypto helpers ---------------------------------------------------------
    def _encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode()) if self._fernet else value.encode()

    def _decrypt(self, blob: bytes) -> str:
        return (self._fernet.decrypt(blob) if self._fernet else blob).decode()

    # -- operations ---------------------------------------------------------------
    def remember(self, value: str, key: str | None = None, source: str = "chat") -> dict:
        if not self.enabled:
            return {"stored": False, "reason": "memory_disabled"}
        cls = self.classifier.classify(value)
        if cls.level == BLOCKED:
            self.audit.log("memory.refused", detail=f"categories={','.join(cls.categories)}",
                           sensitivity=BLOCKED, outcome="refused")
            return {"stored": False, "reason": "blocked_content",
                    "categories": cls.categories}
        key = key or " ".join(value.split()[:5]).lower()
        self.db.execute(
            "INSERT INTO memory (key, value, category, source, created_at) VALUES (?,?,?,?,?)",
            (key, self._encrypt(value), cls.level.lower() if cls.level != "SAFE" else "preference",
             source, datetime.now(timezone.utc).isoformat()),
        )
        self.audit.log("memory.write", target=key)
        return {"stored": True, "key": key}

    def list(self) -> list[dict]:
        rows = self.db.query("SELECT * FROM memory ORDER BY id DESC")
        out = []
        for r in rows:
            try:
                value = self._decrypt(r["value"])
            except Exception:
                value = "(unreadable — key changed)"
            out.append({"id": r["id"], "key": r["key"], "value": value,
                        "category": r["category"], "source": r["source"],
                        "created_at": r["created_at"]})
        return out

    def delete(self, memory_id: int) -> bool:
        cur = self.db.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        deleted = cur.rowcount > 0
        if deleted:
            self.audit.log("memory.delete", target=str(memory_id))
        return deleted

    def clear(self) -> int:
        cur = self.db.execute("DELETE FROM memory")
        self.audit.log("memory.clear", detail=f"removed={cur.rowcount}")
        return cur.rowcount
