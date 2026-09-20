"""Automated name verification and disambiguation gate for candidate sources.

Ensures that before any candidate link is ingested into a person's research session:
1. The subject's name (or a recognized variant/script) explicitly appears in the DOM/title.
2. Homonyms are disambiguated using field, affiliation, and subject keywords.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .multilingual_search import detect_languages, transliterate_name, _INDIC_PHONETIC_MAP


@dataclass
class NameVerificationResult:
    matched: bool
    variant: Optional[str] = None
    snippet: str = ""
    context_matched: bool = False
    homonym_risk: bool = False
    reason: str = "no_name_match"  # matched | no_name_match | homonym_risk


def generate_name_variants(
    name: str,
    nationality: Optional[str] = None,
    extra_aliases: Optional[list[str]] = None,
) -> list[str]:
    """Generate all recognized name variations, initials, and script transliterations."""
    variants: set[str] = set()
    cleaned = name.strip()
    if not cleaned:
        return []

    variants.add(cleaned)

    # Remove titles if present
    base_name = re.sub(r"^(dr\.?|prof\.?|shri|smt\.?|mr\.?|ms\.?|mrs\.?)\s+", "", cleaned, flags=re.I).strip()
    variants.add(base_name)

    parts = base_name.split()
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        variants.add(f"{first} {last}")

        # Initials
        if len(parts) == 2:
            variants.add(f"{first[0]}. {last}")
            variants.add(f"{first[0]}.{last}")
        elif len(parts) >= 3:
            middle = parts[1]
            variants.add(f"{first} {middle[0]}. {last}")
            variants.add(f"{first[0]}. {middle[0]}. {last}")
            variants.add(f"{first[0]}.{middle[0]}. {last}")
            variants.add(f"{first[0]}. {last}")
            variants.add(f"{first[0]}.{last}")

        # Reverse citation format: "Last, First Middle"
        variants.add(f"{last}, {first}")

    # Add honorific forms
    for v in list(variants):
        variants.add(f"Dr. {v}")
        variants.add(f"Prof. {v}")

    # Indic / Devanagari transliteration
    langs = detect_languages(nationality, base_name)
    if "hi" in langs or any(t.lower() in _INDIC_PHONETIC_MAP for t in parts):
        devanagari_full = transliterate_name(base_name, "hi")
        if devanagari_full:
            variants.add(devanagari_full)
            variants.add(f"डॉ. {devanagari_full}")
            variants.add(f"डॉ {devanagari_full}")
            dev_parts = devanagari_full.split()
            if len(dev_parts) >= 3:
                # e.g., पी. एस. यादव
                variants.add(f"पी. एस. {dev_parts[-1]}")
                variants.add(f"पी.एस. {dev_parts[-1]}")

    if extra_aliases:
        for alias in extra_aliases:
            if alias.strip():
                variants.add(alias.strip())

    # Sort longer variants first for regex matching precedence
    return sorted(list(variants), key=lambda x: len(x), reverse=True)


def verify_name_in_content(
    name: str,
    text: str,
    title: str = "",
    field: Optional[str] = None,
    affiliation: Optional[str] = None,
    nationality: Optional[str] = None,
    extra_aliases: Optional[list[str]] = None,
) -> NameVerificationResult:
    """Verify whether the person's name appears in the title or text with disambiguation."""
    combined_content = f"{title}\n\n{text}".strip()
    if not combined_content:
        return NameVerificationResult(matched=False, reason="empty_content")

    variants = generate_name_variants(name, nationality, extra_aliases)
    matched_variant: Optional[str] = None
    match_pos: int = -1

    for v in variants:
        # Match using word boundaries where applicable
        escaped = re.escape(v)
        pattern = rf"(?:\b|_){escaped}(?:\b|_)" if re.search(r"^\w", v) else escaped
        match = re.search(pattern, combined_content, re.IGNORECASE)
        if match:
            matched_variant = v
            match_pos = match.start()
            break

    if not matched_variant or match_pos < 0:
        return NameVerificationResult(
            matched=False,
            reason="no_name_match",
        )

    # Extract context snippet around match
    snippet_start = max(0, match_pos - 100)
    snippet_end = min(len(combined_content), match_pos + 150)
    snippet = combined_content[snippet_start:snippet_end].replace("\n", " ").strip()

    # Context disambiguation
    context_tokens: list[str] = []
    if affiliation:
        # e.g. "CIRB", "Central Institute for Research on Buffaloes", "ICAR"
        context_tokens.extend([t for t in re.split(r"[,;()/\s]+", affiliation) if len(t) > 3])
        # Add acronyms (e.g. CIRB, ICAR, HAU)
        words = affiliation.split()
        if len(words) >= 2:
            acronym = "".join(w[0] for w in words if w[0].isupper())
            if len(acronym) >= 2:
                context_tokens.append(acronym)

    if field:
        context_tokens.extend([t for t in re.split(r"[,;()/\s]+", field) if len(t) > 3])

    context_matched = False
    if not context_tokens:
        # No affiliation or field specified — accept name match
        context_matched = True
    else:
        text_lower = combined_content.lower()
        matched_tokens = [tok for tok in context_tokens if tok.lower() in text_lower]
        if matched_tokens:
            context_matched = True

    # Conflicting profession signals (common homonym collision domains)
    homonym_risk = False
    if not context_matched:
        conflict_patterns = [
            r"\bpolitician\b", r"\bmla\b", r"\bmp\b", r"\belection\b",
            r"\bcricketer\b", r"\bactor\b", r"\bmovie\b", r"\bbollywood\b",
            r"\bpolice\s+officer\b", r"\bgangster\b", r"\badvocate\b"
        ]
        text_lower = combined_content.lower()
        if any(re.search(p, text_lower) for p in conflict_patterns):
            homonym_risk = True

    reason = "matched"
    if homonym_risk:
        reason = "homonym_risk"

    return NameVerificationResult(
        matched=True,
        variant=matched_variant,
        snippet=snippet,
        context_matched=context_matched,
        homonym_risk=homonym_risk,
        reason=reason,
    )
