"""Claim evidence application policies.

Discovery and matching may suggest evidence, but only this boundary mutates a
claim's settled quote and audit trail.
"""

from __future__ import annotations

from typing import Iterable, Any

from .models import PersonProfile, log_claim_verification


def apply_quote_candidates(
    profile: PersonProfile,
    items: Iterable[dict[str, Any]],
    actor: str,
) -> dict:
    """Apply matched quotes to approved, source-bound claims only."""
    updated = 0
    skipped: list[dict[str, Any]] = []
    for item in items:
        idx = item.get("claim_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(profile.claims):
            skipped.append({"claim_index": idx, "why": "bad index"})
            continue

        claim = profile.claims[idx]
        quote = (item.get("quote") or "").strip()
        if not quote or len(quote) < 20:
            skipped.append({"claim_index": idx, "why": "quote too short"})
            continue
        if not claim.draft_approved:
            skipped.append({"claim_index": idx, "why": "claim is not draft-approved"})
            continue
        if not claim.source_url or item.get("source_url") != claim.source_url:
            skipped.append({"claim_index": idx, "why": "source mismatch (guard)"})
            continue

        claim.settled_quote = quote[:800]
        log_claim_verification(
            claim,
            level="claim",
            actor=actor,
            action="backfill_quote",
            verdict="passed",
            summary=f"L4 quote backfilled by {actor} (score {item.get('score')})",
            details={"score": item.get("score"), "quote": quote[:200]},
        )
        updated += 1

    return {"updated": updated, "skipped": skipped}
