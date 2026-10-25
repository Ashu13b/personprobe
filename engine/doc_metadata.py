"""Document Forensics & Metadata Extraction.

Extracts internal metadata, creation timestamps, and author/system attributes
from binary document assets (PDFs, reports, and scans) using PyMuPDF (fitz).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional


def parse_pdf_date(raw_date: Optional[str]) -> Optional[str]:
    """Convert PDF date format (e.g. D:20230706090631+05'30') to clean ISO string."""
    if not raw_date:
        return None
    clean = raw_date.strip().removeprefix("D:")
    # Match YYYYMMDDHHMMSS
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:(\d{2})(\d{2})(\d{2}))?", clean)
    if not m:
        return None
    year, month, day = m.group(1), m.group(2), m.group(3)
    hour, minute, sec = m.group(4) or "00", m.group(5) or "00", m.group(6) or "00"

    tz_str = ""
    tz_match = re.search(r"([+-])(\d{2})'?(\d{2})'?", clean)
    if tz_match:
        sign, tz_h, tz_m = tz_match.group(1), tz_match.group(2), tz_match.group(3)
        tz_str = f"{sign}{tz_h}:{tz_m}"
    elif "Z" in clean:
        tz_str = "+00:00"

    return f"{year}-{month}-{day}T{hour}:{minute}:{sec}{tz_str}"


def extract_pdf_metadata(source: bytes | Path | str) -> dict[str, Any]:
    """Extract structural and forensic metadata from PDF bytes or filepath."""
    try:
        import fitz
    except ImportError:
        return {"error": "PyMuPDF not installed"}

    try:
        if isinstance(source, bytes):
            doc = fitz.open(stream=source, filetype="pdf")
        elif isinstance(source, (Path, str)):
            doc = fitz.open(str(source))
        else:
            return {"error": "Unsupported source type"}

        meta = doc.metadata or {}
        created_iso = parse_pdf_date(meta.get("creationDate"))
        modified_iso = parse_pdf_date(meta.get("modDate"))

        return {
            "title": (meta.get("title") or "").strip(),
            "author": (meta.get("author") or "").strip(),
            "subject": (meta.get("subject") or "").strip(),
            "keywords": (meta.get("keywords") or "").strip(),
            "creator_software": (meta.get("creator") or "").strip(),
            "producer_software": (meta.get("producer") or "").strip(),
            "created_at": created_iso,
            "modified_at": modified_iso,
            "page_count": len(doc),
            "pdf_format": meta.get("format", ""),
            "is_encrypted": bool(doc.is_encrypted),
        }
    except Exception as e:
        return {"error": str(e)}
