"""Shared fixtures: every test runs against a THROWAWAY copy of the sample data
in tmp_path, so gated actions (move/delete) can mutate files safely and nothing
touches the repo's sample_data or real config."""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

import pytest
import yaml

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from maya.audit import AuditLogger              # noqa: E402
from maya.config import Config                  # noqa: E402
from maya.db import Database                    # noqa: E402
from maya.email_connectors import get_connector # noqa: E402
from maya.files import FileIndexer              # noqa: E402
from maya.memory import MemoryManager           # noqa: E402
from maya.orchestrator import ActionGate, Orchestrator  # noqa: E402
from maya.persona import Persona                # noqa: E402
from maya.policy import PolicyEngine            # noqa: E402


@pytest.fixture()
def cfg(tmp_path) -> Config:
    shutil.copytree(REPO / "sample_data" / "workspace", tmp_path / "workspace")
    shutil.copytree(REPO / "sample_data" / "private_vault", tmp_path / "private_vault")
    (tmp_path / "sample_data").mkdir()
    shutil.copytree(REPO / "sample_data" / "emails", tmp_path / "sample_data" / "emails")

    settings = yaml.safe_load((REPO / "config" / "settings.yaml").read_text())
    settings["workspace"]["approved_folders"] = [str(tmp_path / "workspace")]
    settings["storage"]["data_dir"] = str(tmp_path / "data")
    policy = yaml.safe_load((REPO / "config" / "policy.yaml").read_text())
    personality = yaml.safe_load((REPO / "config" / "personality.yaml").read_text())
    return Config(settings=settings, policy=policy, personality=personality, root=tmp_path)


@pytest.fixture()
def db() -> Database:
    return Database(":memory:")


@pytest.fixture()
def audit(db) -> AuditLogger:
    return AuditLogger(db)


@pytest.fixture()
def policy(cfg) -> PolicyEngine:
    return PolicyEngine(cfg)


@pytest.fixture()
def indexer(cfg, db, policy, audit) -> FileIndexer:
    ix = FileIndexer(cfg, db, policy, audit)
    ix.rebuild()
    return ix


@pytest.fixture()
def memory(db, cfg, policy, audit) -> MemoryManager:
    return MemoryManager(db, cfg, policy.classifier, audit)


@pytest.fixture()
def persona(cfg) -> Persona:
    return Persona(cfg.personality, wit_level="classic", rng=random.Random(7))


@pytest.fixture()
def gate(policy, audit, cfg, indexer) -> ActionGate:
    return ActionGate(policy, audit, cfg, on_files_changed=indexer.rebuild)


@pytest.fixture()
def orchestrator(cfg, db, policy, indexer, memory, audit, persona, gate) -> Orchestrator:
    return Orchestrator(
        config=cfg, db=db, policy=policy, indexer=indexer,
        connector=get_connector(cfg), memory=memory, audit=audit,
        persona=persona, gate=gate,
    )
