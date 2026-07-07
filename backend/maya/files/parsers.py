"""Text extraction for supported file types: TXT, MD, CSV, PDF, DOCX.

PDF and DOCX support degrade gracefully when pypdf / python-docx are missing —
those files are simply skipped (with a note), never half-parsed.
"""

from __future__ import annotations

import csv
from pathlib import Path

try:
    from pypdf import PdfReader
    _HAS_PDF = True
except Exception:  # pragma: no cover
    _HAS_PDF = False

try:
    import docx as _docx
    _HAS_DOCX = True
except Exception:  # pragma: no cover
    _HAS_DOCX = False

MAX_CSV_ROWS = 60


def extract_text(path: Path, max_bytes: int = 12 * 1024 * 1024) -> str | None:
    """Return extracted text, or None when the type is unsupported here."""
    if path.stat().st_size > max_bytes:
        return None
    ext = path.suffix.lower()
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".csv":
        return _csv_text(path)
    if ext == ".pdf":
        return _pdf_text(path) if _HAS_PDF else None
    if ext == ".docx":
        return _docx_text(path) if _HAS_DOCX else None
    return None


def _csv_text(path: Path) -> str:
    lines: list[str] = []
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        rows = []
        for i, row in enumerate(reader):
            if i > MAX_CSV_ROWS:
                break
            rows.append(row)
    if not rows:
        return ""
    header = rows[0]
    lines.append("Columns: " + ", ".join(header) + ".")
    for row in rows[1:]:
        cells = [f"{h}: {v}" for h, v in zip(header, row) if v.strip()]
        lines.append("; ".join(cells) + ".")
    total = len(rows) - 1
    lines.append(f"Table with {total} data rows{' (truncated)' if total > MAX_CSV_ROWS - 1 else ''}.")
    return "\n".join(lines)


def _pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages[:80]]
    return "\n".join(pages)


def _docx_text(path: Path) -> str:
    document = _docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)
