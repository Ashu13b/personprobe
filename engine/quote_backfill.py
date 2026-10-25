"""Find the source sentence that substantiates a claim (L4 evidence backfill).

Claims approved earlier carry no verbatim quote, so an outside reviewer cannot
re-derive them. This module locates the best supporting sentence in the cited
page: token-overlap scoring over sentence windows, with date/number
normalization so paraphrases ("Born on 10 April 1963") match source wording
("Born on April 10, 1963").
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

_MARKUP_RE = re.compile(
    r"(?:var\s+[a-zA-Z_$][0-9a-zA-Z_$]*\s*=|function\s*\([^\)]*\)\s*\{|function\s+[a-zA-Z_$][0-9a-zA-Z_$]*\s*\(|"
    r"@type|@context|&quot;|&amp;|&#|_id|\bslug\b|https?://|</?div\b|</?span\b|\{\"|\"\}|</?img\b|staticimg|"
    r"\bmw-|data-|::|\b\d+px\b)",
    re.I,
)

_NAV_RE = re.compile(
    r"(?:add\s+\w+\s+as your trusted source|subscribe|sign in|log ?in|privacy policy|newsletter|cookie|all rights reserved|powered by|facebook\s+twitter|facebook\s+linkedin|whatsapp)",
    re.I,
)

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "in",
    "at",
    "on",
    "for",
    "to",
    "from",
    "by",
    "with",
    "was",
    "were",
    "is",
    "are",
    "be",
    "as",
    "that",
    "this",
    "his",
    "her",
    "their",
    "under",
    "during",
    "into",
    "also",
    "he",
    "she",
    "they",
    "it",
    "reported",
    "stated",
    "said",
    "according",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 1}


def _norm_dates(text: str) -> str:
    """Normalize date forms for matching: '10 April 1963' and 'April 10, 1963' -> tokens."""
    t = (text or "").lower()
    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    for i, m in enumerate(months, 1):
        t = re.sub(rf"\b{i}\s+{m}\b", f"{m}", t)  # 10 april -> april
        t = re.sub(rf"\b{m}\s+(\d{{1,2}})", lambda mo, mm=m: f"{mm} {mo.group(1)}", t)
    t = t.replace(",", " ")
    return t


def sentences(text: str) -> list[str]:
    masked = re.sub(
        r"\b(Dr|Sh|Mr|Mrs|Ms|Prof|Late|Rs|No|Vol|pp|vs)\.",
        r"\1__DOT__",
        text or "",
        flags=re.I,
    )
    parts = re.split(r"(?<=[.!?;])\s+|\n\s*\n+", masked)
    cleaned = []
    for p in parts:
        flat = re.sub(r"\s+", " ", p.replace("__DOT__", ".")).strip()
        if len(flat) > 20:
            cleaned.append(flat)
    return cleaned


def best_quote(
    claim_text: str,
    page_text: str,
    *,
    min_score: float = 0.42,
    window: int = 2,
    must_include_any: Optional[list[str]] = None,
) -> tuple[Optional[str], float]:
    """Return (best supporting quote, score) from page_text for claim_text.

    Scores sentence windows (1-`window` sentences) by token containment of the
    claim, boosted when the window carries the same years/numbers. Returns
    (None, score) below `min_score` rather than inventing support.
    """
    claim_tokens = _tokens(_norm_dates(claim_text))
    claim_nums = set(
        re.findall(r"\b(?:1[5-9]\d{2}|20\d{2}|\d{2,})\b", _norm_dates(claim_text))
    )
    if not claim_tokens:
        return None, 0.0

    sents = sentences(page_text)
    if not sents:
        return None, 0.0

    def _is_natural_language(chunk: str) -> bool:
        if _MARKUP_RE.search(chunk) or _NAV_RE.search(chunk):
            return False
        words = re.findall(r"[A-Za-z]{3,}", chunk)
        return len(words) >= 6

    best: tuple[float, str] = (0.0, "")
    for i in range(len(sents)):
        for w in range(1, window + 1):
            chunk = " ".join(sents[i : i + w])
            if not _is_natural_language(chunk):
                continue
            if must_include_any and not any(
                m.lower() in chunk.lower() for m in must_include_any
            ):
                continue
            chunk_norm = _norm_dates(chunk)
            chunk_tokens = _tokens(chunk_norm)
            if not chunk_tokens:
                continue
            overlap = len(claim_tokens & chunk_tokens) / len(claim_tokens)
            if claim_nums:
                nums = set(
                    re.findall(r"\b(?:1[5-9]\d{2}|20\d{2}|\d{2,})\b", chunk_norm)
                )
                if nums & claim_nums:
                    overlap += 0.10
            if len(chunk) > 420:
                overlap -= 0.05
            if overlap > best[0]:
                best = (overlap, chunk.strip())
    if best[0] < min_score or len(best[1]) < 40:
        return None, round(best[0], 3)
    res = best[1]
    if len(res) > 600:
        if must_include_any:
            pos = -1
            for m in must_include_any:
                idx = res.lower().find(m.lower())
                if idx >= 0:
                    pos = idx
                    break
            if pos >= 0:
                start = max(0, pos - 150)
                res = res[start : start + 600].strip()
            else:
                res = res[:600]
        else:
            res = res[:600]
    return res, round(best[0], 3)


def collect_claims_needing_quotes(
    claims: Iterable, approved_only: bool = True
) -> list[int]:
    out = []
    for i, c in enumerate(claims):
        if approved_only and not getattr(c, "draft_approved", False):
            continue
        if getattr(c, "settled_quote", None):
            continue
        if not getattr(c, "source_url", None):
            continue
        out.append(i)
    return out
