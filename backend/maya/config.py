"""Configuration loading for MAYA.

Three YAML files under config/ drive the system:
  settings.yaml     — what MAYA may touch (folders, labels), voice, memory, server
  policy.yaml       — sensitivity classifier rules, redaction patterns, action risk
  personality.yaml  — tone, quip pools, guardrails

Tests may construct Config directly from dicts to point at temp folders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


class Config:
    def __init__(
        self,
        settings: dict,
        policy: dict,
        personality: dict,
        root: Path | None = None,
    ):
        self.root = Path(root) if root else REPO_ROOT
        self.settings = settings or {}
        self.policy = policy or {}
        self.personality = personality or {}

    @classmethod
    def load(cls, root: Path | None = None) -> "Config":
        root = Path(root) if root else REPO_ROOT
        cfg_dir = root / "config"

        def read(name: str) -> dict:
            p = cfg_dir / name
            if not p.exists():
                return {}
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

        return cls(
            settings=read("settings.yaml"),
            policy=read("policy.yaml"),
            personality=read("personality.yaml"),
            root=root,
        )

    # -- generic dotted access ------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.settings
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    # -- workspace ------------------------------------------------------------
    @property
    def approved_folders(self) -> list[Path]:
        out = []
        for raw in self.get("workspace.approved_folders", []) or []:
            p = Path(raw)
            out.append(p if p.is_absolute() else (self.root / p).resolve())
        return out

    @property
    def denied_patterns(self) -> list[str]:
        return [str(x).lower() for x in self.get("workspace.denied_patterns", []) or []]

    @property
    def allowed_extensions(self) -> set[str]:
        exts = self.get("workspace.allowed_extensions", [".txt", ".md", ".csv"])
        return {str(e).lower() for e in exts}

    @property
    def max_file_bytes(self) -> int:
        return int(self.get("workspace.max_file_mb", 12)) * 1024 * 1024

    # -- storage ---------------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        raw = self.get("storage.data_dir", "data")
        p = Path(raw)
        p = p if p.is_absolute() else self.root / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    # -- email -----------------------------------------------------------------
    @property
    def approved_labels(self) -> list[str]:
        return self.get("email.approved_labels", ["INBOX"]) or ["INBOX"]

    @property
    def vip_senders(self) -> list[str]:
        return [s.lower() for s in self.get("email.vip_senders", []) or []]

    # -- voice / persona --------------------------------------------------------
    @property
    def wake_phrases(self) -> list[str]:
        return [w.lower() for w in self.get("voice.wake_phrases", ["maya"]) or ["maya"]]

    @property
    def wit_level(self) -> str:
        return str(self.get("persona.wit_level", "classic"))
