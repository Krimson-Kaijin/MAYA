"""Personality guardrails: wit budget, no repeats, zero humor in sensitive contexts."""

import random

from maya.persona import Persona


def make_persona(cfg, level="classic", seed=7):
    return Persona(cfg.personality, wit_level=level, rng=random.Random(seed))


def test_core_answer_always_first(cfg):
    p = make_persona(cfg)
    for _ in range(30):
        out = p.compose("Found the file.", pool="file_found")
        assert out.startswith("Found the file.")


def test_wit_budget_and_no_consecutive_quips(cfg):
    p = make_persona(cfg)
    witty_flags = []
    for _ in range(60):
        out = p.compose("Core.", pool="file_found")
        witty_flags.append(out != "Core.")
    assert any(witty_flags), "classic wit level should produce some quips"
    assert not all(witty_flags), "quips must not appear on every reply"
    for a, b in zip(witty_flags, witty_flags[1:]):
        assert not (a and b), "never two witty replies in a row"


def test_quips_come_only_from_reviewed_pools(cfg):
    p = make_persona(cfg)
    pool = set(cfg.personality["quips"]["file_found"])
    for _ in range(60):
        out = p.compose("Core.", pool="file_found")
        if out != "Core.":
            assert out[len("Core. "):] in pool


def test_no_humor_for_sensitive_content(cfg):
    p = make_persona(cfg)
    for _ in range(60):
        assert p.compose("Summary ready.", pool="summary_done",
                         sensitivity="SENSITIVE") == "Summary ready."
        assert p.compose("Summary ready.", pool="summary_done",
                         sensitivity="BLOCKED") == "Summary ready."


def test_wit_off_silences_everything(cfg):
    p = make_persona(cfg, level="off")
    for _ in range(60):
        assert p.compose("Core.", pool="file_found") == "Core."


def test_refusal_is_plain_and_respectful(cfg):
    p = make_persona(cfg)
    text = p.refusal(["banking", "credentials"])
    assert "privacy policy" in text
    assert "Shockingly" not in text and "bold" not in text  # no quip leakage


def test_refusals_never_witty_even_at_max_wit(cfg):
    p = make_persona(cfg)
    outs = {p.refusal(["payroll"]) for _ in range(20)}
    assert len(outs) == 1  # deterministic, no randomized humor
