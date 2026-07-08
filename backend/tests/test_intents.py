"""Voice/chat command parsing — including the brief's four canonical commands."""

from maya.orchestrator.intents import parse_command

WAKE = ["maya", "hey maya", "ok maya"]


def test_brief_command_email_digest():
    i = parse_command("MAYA, summarize today's important emails.", WAKE)
    assert i.name == "email_digest"


def test_brief_command_find_latest_sop():
    i = parse_command("MAYA, find the latest logistics SOP.", WAKE)
    assert i.name == "find_file"
    assert i.slots["latest"] is True
    assert "logistics" in i.slots["query"] and "sop" in i.slots["query"]


def test_brief_command_compare_these_two():
    i = parse_command("MAYA, compare these two files.", WAKE)
    assert i.name == "compare_files"
    assert i.slots.get("use_context") is True


def test_brief_command_prioritize_today():
    i = parse_command("MAYA, what should I prioritize today?", WAKE)
    assert i.name == "briefing"


def test_wake_phrase_variants():
    for prefix in ("Hey Maya,", "ok maya", "Maya:"):
        i = parse_command(f"{prefix} summarize my inbox", WAKE)
        assert i.name == "email_digest", prefix


def test_compare_with_names():
    i = parse_command('compare "logistics_sop_v2.md" and "logistics_sop_v3.md"', WAKE)
    assert i.name == "compare_files"
    assert i.slots["a"] == "logistics_sop_v2.md"
    assert i.slots["b"] == "logistics_sop_v3.md"


def test_summarize_with_mode_and_ordinal():
    i = parse_command("summarize the second one in detail", WAKE)
    assert i.name == "summarize_file"
    assert i.slots["ordinal"] == 2
    assert i.slots["mode"] == "detailed"


def test_summarize_named_doc():
    i = parse_command("Maya, summarize the vendor review briefly", WAKE)
    assert i.name == "summarize_file"
    assert i.slots["mode"] == "short"
    assert "vendor review" in i.slots["query"]


def test_brief_me_on_is_summarize_not_briefing():
    i = parse_command("brief me on the festival campaign notes", WAKE)
    assert i.name == "summarize_file"


def test_move_and_delete_are_parsed():
    i = parse_command("move the festival campaign notes to archive", WAKE)
    assert i.name == "move_file"
    assert i.slots["dest"] == "archive"
    j = parse_command("delete the vendor review", WAKE)
    assert j.name == "delete_file"
    assert "vendor review" in j.slots["query"]


def test_confirm_and_cancel():
    assert parse_command("confirm", WAKE).name == "confirm"
    assert parse_command("yes, go ahead", WAKE).name == "confirm"
    assert parse_command("cancel", WAKE).name == "cancel"
    assert parse_command("never mind", WAKE).name == "cancel"


def test_memory_commands():
    i = parse_command("remember that I prefer short summaries", WAKE)
    assert i.name == "remember"
    assert "short summaries" in i.slots["value"]
    assert parse_command("what do you know about me?", WAKE).name == "memory_show"
    f = parse_command("forget about the tagline", WAKE)
    assert f.name == "memory_forget"


def test_reminder():
    i = parse_command("Maya, remind me to send the surge plan on Friday", WAKE)
    assert i.name == "remind"
    assert "surge plan" in i.slots["value"]


def test_draft_reply_with_ordinal():
    i = parse_command("draft a reply to the first one", WAKE)
    assert i.name == "draft_reply"
    assert i.slots["ordinal"] == 1


def test_find_without_query_asks_clarification():
    i = parse_command("Maya, find", WAKE)
    assert i.name == "find_file"
    assert i.clarify


def test_bare_wake_word_greets():
    assert parse_command("Maya?", WAKE).name == "greeting"


def test_unknown_falls_through():
    assert parse_command("purple monkey dishwasher", WAKE).name == "unknown"
