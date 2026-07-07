"""Memory: explicit storage, blocked-value refusal, encryption at rest, toggle."""


def test_remember_and_list(memory):
    out = memory.remember("I prefer short summaries in the morning")
    assert out["stored"]
    items = memory.list()
    assert len(items) == 1
    assert "short summaries" in items[0]["value"]


def test_blocked_value_refused(memory):
    out = memory.remember("my card number is 4539 1488 0343 6467")
    assert not out["stored"]
    assert out["reason"] == "blocked_content"
    assert memory.list() == []


def test_encrypted_at_rest(memory, db):
    memory.remember("the festival campaign tagline is Pandagaku Time-ki")
    row = db.query_one("SELECT value FROM memory")
    raw = row["value"]
    blob = raw if isinstance(raw, bytes) else str(raw).encode()
    assert b"Pandagaku" not in blob   # ciphertext, not plaintext
    assert "Pandagaku" in memory.list()[0]["value"]  # decrypts fine


def test_delete(memory):
    memory.remember("temporary preference")
    mid = memory.list()[0]["id"]
    assert memory.delete(mid)
    assert memory.list() == []


def test_toggle_off_blocks_writes(memory):
    memory.set_enabled(False)
    out = memory.remember("should not be stored")
    assert not out["stored"]
    assert out["reason"] == "memory_disabled"
    memory.set_enabled(True)
    assert memory.remember("stored again")["stored"]


def test_memory_ops_are_audited(memory, audit):
    memory.remember("audited preference")
    events = [e["event"] for e in audit.recent()]
    assert "memory.write" in events
