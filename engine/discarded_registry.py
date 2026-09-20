"""Registry for rejected and discarded candidate links with canonical deduplication.

Serves two essential purposes:
1. Auditability & Recovery: Preserves discarded candidate links with their title,
   snippet, and reason (e.g. 'no_name_match'). If human or agent discovers an
   alternative name variation (Devanagari script, alias, or typo), the link can be
   re-evaluated and recovered.
2. Canonical Deduplication: Ensures discovery engines, crawlers, and AI agents
   never re-crawl, re-fetch, or re-recommend previously discarded URLs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .canonical_url import canonical_url
from .models import DiscardedSource, PersonProfile


def record_discarded(
    profile: PersonProfile,
    url: str,
    reason: str = "no_name_match",
    title: str = "",
    snippet: str = "",
    name_checked: str = "",
) -> DiscardedSource:
    """Record a URL into the profile's discarded registry with canonical deduplication.

    Reasons:
    - 'no_name_match': page loaded but name not found in DOM
    - 'off_topic': mentions subject name but content is entirely unrelated
    - 'homonym': mentions a different person with the same name
    - 'dead': returned 404/410 with no archive
    - 'user_rejected': explicitly rejected by human reviewer
    - 'paywall': unreadable behind login or hard paywall
    - 'redundant': duplicate coverage of identical content
    """
    c_url = canonical_url(url)
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Check for existing entry in discarded_sources
    for existing in profile.discarded_sources:
        if existing.canonical_url == c_url:
            if title and not existing.title:
                existing.title = title
            if snippet and not existing.snippet:
                existing.snippet = snippet
            if name_checked and not existing.name_checked:
                existing.name_checked = name_checked
            return existing

    discarded = DiscardedSource(
        url=url,
        canonical_url=c_url,
        title=title.strip() if title else "",
        reason=reason,
        name_checked=name_checked or profile.name,
        snippet=snippet.strip()[:600] if snippet else "",
        date_recorded=date_str,
    )
    profile.discarded_sources.append(discarded)

    # Maintain backward compatibility with legacy rejected_sources list
    if url not in profile.rejected_sources:
        profile.rejected_sources.append(url)

    return discarded


def is_discarded(profile: PersonProfile, url: str) -> bool:
    """Check whether a URL has been discarded or rejected."""
    c_url = canonical_url(url)
    for d in profile.discarded_sources:
        if d.canonical_url == c_url:
            return True
    for u in getattr(profile, "rejected_sources", []) or []:
        if canonical_url(u) == c_url:
            return True
    for u in getattr(profile, "skipped_sources", []) or []:
        if canonical_url(u) == c_url:
            return True
    return False


def is_known_or_discarded(profile: PersonProfile, url: str) -> bool:
    """Check whether a URL is already an active source OR discarded/rejected/skipped."""
    c_url = canonical_url(url)
    for s in profile.sources:
        if canonical_url(s.url) == c_url:
            return True
    return is_discarded(profile, url)


def get_known_and_discarded_canonical_urls(profile: PersonProfile) -> set[str]:
    """Return set of all canonical URLs from active sources, discarded, rejected, and skipped."""
    seen: set[str] = set()
    for s in profile.sources:
        seen.add(canonical_url(s.url))
    for d in profile.discarded_sources:
        seen.add(d.canonical_url)
    for u in getattr(profile, "rejected_sources", []) or []:
        seen.add(canonical_url(u))
    for u in getattr(profile, "skipped_sources", []) or []:
        seen.add(canonical_url(u))
    return seen


def recover_discarded(profile: PersonProfile, url: str) -> Optional[DiscardedSource]:
    """Remove a URL from the discarded registry so it can be re-evaluated or accepted."""
    c_url = canonical_url(url)
    recovered: Optional[DiscardedSource] = None

    filtered_discarded: list[DiscardedSource] = []
    for d in profile.discarded_sources:
        if d.canonical_url == c_url:
            recovered = d
        else:
            filtered_discarded.append(d)
    profile.discarded_sources = filtered_discarded

    # Also remove from rejected_sources and skipped_sources if present
    profile.rejected_sources = [
        u for u in profile.rejected_sources if canonical_url(u) != c_url and u != url
    ]
    profile.skipped_sources = [
        u for u in profile.skipped_sources if canonical_url(u) != c_url and u != url
    ]

    return recovered


def get_discarded_by_reason(profile: PersonProfile, reason: str) -> list[DiscardedSource]:
    """Filter discarded sources by specific reason (e.g. 'no_name_match')."""
    return [d for d in profile.discarded_sources if d.reason == reason]
