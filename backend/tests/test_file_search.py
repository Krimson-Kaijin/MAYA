"""File indexing and search: approved folders only, filters, latest-ranking."""

from maya.files.search import search_index


def test_index_covers_workspace(indexer):
    assert indexer.count() >= 8  # all sample workspace docs


def test_private_vault_never_indexed(indexer, db):
    rows = db.query("SELECT path FROM file_index")
    assert all("private_vault" not in r["path"] for r in rows)
    hits = search_index(db, "router password")
    assert hits == []


def test_blocked_file_metadata_only(indexer, db):
    row = db.query_one("SELECT * FROM file_index WHERE name = 'bank_statement_june.txt'")
    assert row is not None
    assert row["sensitivity"] == "BLOCKED"
    assert row["text"] == ""  # content is never stored for blocked files


def test_keyword_search_finds_doc(indexer, db):
    hits = search_index(db, "vendor performance review")
    assert hits and hits[0].name == "q2_vendor_review.txt"


def test_latest_prefers_newer_version(indexer, db):
    hits = search_index(db, "logistics sop", latest=True)
    assert hits[0].name == "logistics_sop_v3.md"
    names = [h.name for h in hits]
    assert "logistics_sop_v2.md" in names


def test_type_filter(indexer, db):
    hits = search_index(db, "", ftype="csv")
    assert hits and all(h.ext == ".csv" for h in hits)


def test_folder_filter(indexer, db):
    hits = search_index(db, "", folder="meetings")
    assert hits and all("meetings" in h.folder for h in hits)


def test_shielded_hit_has_no_snippet(indexer, db):
    hits = search_index(db, "bank statement")
    shielded = [h for h in hits if h.shielded]
    assert shielded, "blocked file should still be listable by name"
    assert all(h.snippet == "" for h in shielded)
