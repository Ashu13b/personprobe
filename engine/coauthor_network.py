"""Person-adjacent profile harvesting (co-author / collaborator networks).

Research engines commonly expose a subject's profile plus the graph of the
people who co-sign their work (Vidwan/IRINS, ORCID, publisher author pages).
Each co-author profile is a *person-adjacent source*: it routinely contains
exact author-list mentions of our subject on records that are not on the
subject's own profile page. This is general engine output fetched for any
subject — no site-specific logic lives here beyond the parser registry.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Iterable, Optional

from .models import PersonProfile, Source, SourceReliability
from .name_verifier import verify_name_in_content, assess_namesake_risk


def _coauthor_mention_note(host: str, matched_variant: str) -> str:
    return f"co-author network mention found on {host}: variant '{matched_variant}'"


def extract_subject_mentions(profile: PersonProfile, html_text: str) -> Optional[dict]:
    """Check a co-author profile body for mentions of our subject."""
    v = verify_name_in_content(
        profile.name, html_text[:200_000], title=profile.name,
        field=profile.field, affiliation=profile.affiliation,
        nationality=profile.nationality,
    )
    if not v.matched:
        return None
    return {"variant": v.variant, "strength": v.identity_strength, "snippet": v.snippet}


def screen_coauthor_page(profile: PersonProfile, url: str, text: str) -> Optional[Source]:
    """Return a Source when a co-author page evidences our subject, else None.

    Applies both the spelling-strength gate and the session namesake registry;
    weak (initials-only for a shared surname) mentions are attached as suspect so
    a human adjudicates, consistent with the ingest policy.
    """
    risk, note = assess_namesake_risk(text, profile.name, profile.known_namesakes)
    if risk == "known_conflict":
        return None
    mention = extract_subject_mentions(profile, text)
    if not mention:
        return None
    strength = mention["strength"]
    host_note = _coauthor_mention_note(re.sub(r'^https?://(www\.)?', '', url), mention["variant"])
    snip = mention["snippet"][:400]
    s = Source(
        url=url,
        title=f"Co-author page mention: {mention['variant']} on network profile",
        publisher=re.split(r'[/?#]', url)[2] if '//' in url else "network",
        reliability=SourceReliability.primary,
        snippet=snip,
        research_notes=(note or ''),
        is_independent=False,
        provenance_category="authored_publication",
        fetched_by="coauthor_network",
        identity_status=("confirmed" if strength == "full" and risk == "none" else "suspect"),
        identity_note=strength.lower() + "-strength variant; " + (note or host_note),
        name_hit_in_body=True,
        name_hit_variant=mention["variant"],
    )
    # L2 identity audit at ingest — suspect never auto-extracts
    return s


def coauthor_source_batch(profile: PersonProfile, pages: Iterable[tuple[str, str]]) -> list[Source]:
    """Build a batch from (url, text) tuples harvested by any transport layer."""
    good = []
    for url, text in pages:
        s = screen_coauthor_page(profile, url, text)
        if s:
            good.append(s)
    return good
