"""Research, source, and claim routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import store

from . import pipelines
from .schemas import (
    IdentifyRequest, ResearchRequest, AddSourceRequest, AddDocumentFact,
    AddSourcedClaimRequest, VerifyClaimRequest, BatchVerifyClaimsRequest, AddSourcePaste, CrawlRequest,
    TargetedSearchRequest, FindIdsRequest, RefreshPapersRequest, AssessSourceRequest,
    VerifySourceLevelRequest, AddNamesakeRequest,
)

from engine.models import (
    PersonProfile, Claim, VerificationState, SourceReliability,
    log_source_verification, log_claim_verification, KnownNamesake,
)
from engine.researcher import (
    fetch_auto_sources, fetch_url_source, fetch_url_source_with_paste,
    fetch_institution_sources, targeted_slot_search,
)
from engine.classifier import classify_sources
from engine.notability import score_notability
from engine.extractor import extract_claims, find_missing_slots
from engine.relevance import flag_sources
from engine.crawler import crawl
from engine.researcher_ids import (
    extract_ids_from_sources,
    is_sd_article_url,
    is_sd_author_url,
    validated_new_ids,
)
from engine.provenance import normalize_url
from engine.canonical_url import canonical_url
from engine.discarded_registry import (
    record_discarded,
    get_known_and_discarded_canonical_urls,
    recover_discarded,
)
from engine.name_verifier import verify_name_in_content, assess_namesake_risk
from adapters.wiki.wiki_check import check_existing_page

research_router = APIRouter()


def _namesake_check(profile, content: str, title: str = "", matched_variant: str | None = None):
    """Session-scoped namesake screen: known_conflict drops the source, possible flags it."""
    return assess_namesake_risk(f"{title}\n{content}", profile.name, profile.known_namesakes, matched_variant)

@research_router.post("/identify")
def identify(req: IdentifyRequest) -> dict:
    """Preview identity clues to confirm the right person.

    Wikipedia/Wikidata candidates carry stable identifiers (wikidata_id,
    wikipedia_url) the user can confirm into the session; generic web snippets
    are corroborating clues only.
    """
    hints = " ".join(x for x in (req.field, req.affiliation) if x)
    identity = []
    try:
        from engine.identifier import find_candidates
        identity = find_candidates(req.name, hints)
    except Exception:
        identity = []

    web = []
    try:
        from engine.researcher import _google_cse, _duckduckgo_html
        web = _google_cse(req.name, req.field, req.affiliation) or _duckduckgo_html(req.name, req.field, req.affiliation) or []
    except Exception:
        web = []

    results = [
        {
            "kind": "identity",
            "title": c.name,
            "url": c.wikipedia_url or f"https://www.wikidata.org/wiki/{c.wikidata_id}",
            "snippet": c.bio_snippet or "",
            "publisher": "Wikipedia/Wikidata",
            "wikidata_id": c.wikidata_id,
            "wikipedia_url": c.wikipedia_url,
            "photo_url": c.photo_url,
            "birth_year": c.birth_year,
            "nationality": c.nationality,
            "field": c.field,
            "affiliation": c.affiliation,
        }
        for c in identity
    ]
    results += [
        {"kind": "web", "title": s.title, "url": s.url, "snippet": s.snippet, "publisher": s.publisher}
        for s in web[:5]
    ]

    # Show the Wikimedia routing outcome up front so the user knows before
    # starting whether this will be new-article or existing-article/draft mode.
    # Prefer the confirmed identity match's article title when one is offered.
    wiki_status = None
    try:
        from adapters.wiki.wiki_check import check_existing_page, check_title_for
        title = check_title_for(req.name, identity[0].wikipedia_url) if identity and identity[0].wikipedia_url else req.name
        wiki_status = check_existing_page(title).model_dump()
    except Exception:
        wiki_status = None

    return {"results": results, "wiki_status": wiki_status}


def _find_resumable_session(req: ResearchRequest) -> PersonProfile | None:
    """Check in-memory store and disk for an existing session with matching identity."""
    existing = next(
        (p for p in store._sessions.values()
         if store._identity_matches({"name": p.name, "wikidata_id": p.wikidata_id},
                                    req.name, req.wikidata_id)),
        None)
    if existing is None:
        hit = store._find_session_on_disk(
            lambda d: store._identity_matches(d, req.name, req.wikidata_id))
        if hit is not None:
            data, path = hit
            profile = PersonProfile(**data["profile"])
            existing = store._activate_session(
                profile, data.get("wiki_status", {"status": "clear", "url": None, "note": None}))
            sid = store._ensure_session_id(existing)
            store._save_session(sid)
            id_path = store._session_path(sid)
            if path != id_path and id_path.exists():
                path.unlink()  # drop the legacy name-based file now migrated
    return existing


def _enrich_and_flag_sources(sources: list, name: str, field: str = "", affiliation: str = "") -> list:
    """Enrich sources with classification, DOI verification, and relevance flags."""
    if not sources:
        return sources
    classified = classify_sources(sources, store.llm())
    store._check_doi_sources(classified, name, affiliation or "")
    flag_sources(classified, name, field or "", affiliation or "")
    return classified


def _populate_initial_sources(profile: PersonProfile, req: ResearchRequest) -> None:
    """Fetch, classify, and filter initial sources for a newly created session."""
    sources, s2_author_id = fetch_auto_sources(req.name, req.field, req.affiliation)
    if s2_author_id:
        profile.researcher_ids["semantic_scholar"] = s2_author_id

    found_ids = extract_ids_from_sources(sources)
    new_ids = {t: v for t, v in found_ids.items() if t not in profile.researcher_ids}
    for id_type, id_val in validated_new_ids(new_ids, req.name, req.affiliation).items():
        profile.researcher_ids[id_type] = id_val

    if req.affiliation:
        institution_sources = fetch_institution_sources(req.name, req.affiliation)
        existing_urls = {s.url for s in sources}
        sources.extend(s for s in institution_sources if s.url not in existing_urls)

    sources = _enrich_and_flag_sources(sources, req.name, req.field or "", req.affiliation or "")
    profile.sources = [s for s in sources if s.relevance_flag != "likely_wrong"]
    profile.claims = []
    profile.notability = score_notability(req.name, [])
    profile.missing_slots = find_missing_slots(profile, [])


@research_router.post("/research/start")
def research_start(req: ResearchRequest) -> dict:
    """Initialize session, run wiki check, fetch + classify sources, score notability.

    Same-identity collision policy: if a session with the same display name AND a
    matching identity hint already exists (wikidata_id equal, or neither has one),
    it is resumed instead of creating a duplicate. Same name with a different
    identity hint creates a distinct session — same-named people never collide.
    """
    existing = _find_resumable_session(req)
    if existing is not None:
        sid = store._ensure_session_id(existing)
        return {
            "wiki_status": store._wiki_statuses.get(sid),
            "notability": existing.notability.model_dump() if existing.notability else None,
            "profile": existing.model_dump(),
            "resumed": True,
        }

    from adapters.wiki.wiki_check import check_title_for
    wiki_status = check_existing_page(check_title_for(req.name, req.wikipedia_url))

    photo_url = req.photo_url
    if not photo_url and req.wikidata_id:
        from engine.identifier import fetch_wikidata_photo_by_id
        photo_url = fetch_wikidata_photo_by_id(req.wikidata_id)

    profile = PersonProfile(
        name=req.name,
        session_id=store._new_session_id(req.name),
        wikidata_id=req.wikidata_id,
        wikipedia_url=req.wikipedia_url,
        photo_url=photo_url,
        field=req.field,
        affiliation=req.affiliation,
        nationality=req.nationality,
        birth_date=req.birth_year,
    )
    _populate_initial_sources(profile, req)

    sid = store._ensure_session_id(profile)
    with store._lock:
        store._sessions[sid] = profile
        store._wiki_statuses[sid] = wiki_status.model_dump()
    store._save_session(sid)

    return {
        "wiki_status": wiki_status.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
        "profile": profile.model_dump(),
        "resumed": False,
    }

@research_router.post("/research/add-source")
def add_source(req: AddSourceRequest) -> dict:
    """User pastes a URL — fetch it, classify it, extract claims from it.

    Special cases:
    - ScienceDirect article URL: resolved via PII→CrossRef→OpenAlex pipeline
    - ScienceDirect author URL: Scopus ID extracted, stored in researcher_ids
    """
    profile = store._get_profile(req.profile_name)
    url = req.url

    if any(canonical_url(s.url) == canonical_url(url) for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    # ── ScienceDirect article: use PII pipeline instead of fetching ───────────
    if is_sd_article_url(url):
        return pipelines._add_sd_article(profile, url)

    # ── ScienceDirect author profile: extract Scopus ID + fetch OpenAlex works ─
    if is_sd_author_url(url):
        return pipelines._add_sd_author_profile(profile, url)

    # ── Source fetch (direct paste or network) ────────────────────────────────
    if req.text:
        source = fetch_url_source_with_paste(url, req.text)
        if req.title:
            source.title = req.title
        source.fetched_by = "browser"
        blocked = False
    else:
        source, blocked = fetch_url_source(url, profile.name)
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    source.liveness = "blocked" if blocked else "alive"

    risk, risk_note = _namesake_check(profile, source.snippet or "", source.title or "", source.identity_note)
    if risk == "known_conflict":
        record_discarded(profile, url, reason="namesake", title=source.title, snippet=source.snippet, name_checked=profile.name)
        raise HTTPException(409, {"message": "Source text matches a session-known namesake; not attached.", "note": risk_note})
    if risk == "possible":
        source.identity_status = "suspect"
        source.identity_note = risk_note

    # Extract researcher IDs from the new URL (e.g. user pastes an ORCID link)
    new_ids = {
        t: v for t, v in extract_ids_from_sources([source]).items()
        if t not in profile.researcher_ids
    }
    for id_type, id_val in validated_new_ids(new_ids, profile.name, profile.affiliation).items():
        profile.researcher_ids[id_type] = id_val

    if url in profile.rejected_sources:
        profile.rejected_sources.remove(url)
    if url in profile.skipped_sources:
        profile.skipped_sources.remove(url)
    recover_discarded(profile, url)

    profile.sources.append(source)
    # Claims are extracted on confirmation, not on add
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    # If blocked, push to human browser_server if it's running
    sent_to_browser = False
    if blocked:
        sent_to_browser = store._push_to_browser(url)

    return {
        "source": source.model_dump(),
        "blocked": blocked,
        "sent_to_browser": sent_to_browser,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@research_router.post("/research/add-document-fact")
def add_document_fact(req: AddDocumentFact) -> dict:
    """User types a fact from a document — no URL, timeline-only, marked unsourced."""
    profile = store._get_profile(req.profile_name)
    claim = Claim(
        text=req.text,
        field=req.field,
        source_url=None,          # no web source
        verification=VerificationState.unverified,
        user_provided=True,
        auto_source_attempted=False,
    )
    profile.claims.append(claim)
    return {"claim": claim.model_dump()}


@research_router.post("/research/add-sourced-claim")
def add_sourced_claim(req: AddSourcedClaimRequest) -> dict:
    """Bind a fact the user read in a source to that source's URL.

    The source must already be in the session. The claim is created confirmed and
    user-provided; draft approval remains a separate explicit action, so a fact
    cannot enter the draft until the user both verifies the source and approves it.
    """
    profile = store._get_profile(req.profile_name)
    if not any(s.url == req.url for s in profile.sources):
        raise HTTPException(400, "Source URL is not in this session; add the source first.")
    claim = Claim(
        text=req.text,
        field=req.field,
        source_url=req.url,
        verification=VerificationState.confirmed,
        user_provided=True,
        date_context=req.date_context,
    )
    source = next(s for s in profile.sources if s.url == req.url)
    from engine.provenance import evaluate_claim_trust
    claim = evaluate_claim_trust(claim, source, profile)
    profile.claims.append(claim)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "claim": claim.model_dump(),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/verify-claim")
def verify_claim(name: str, req: VerifyClaimRequest) -> dict:
    profile = store._get_profile(name)
    if req.claim_index >= len(profile.claims):
        raise HTTPException(400, "claim_index out of range")

    claim = profile.claims[req.claim_index]
    actor = req.actor or "human"

    if req.action == "confirm":
        claim.verification = VerificationState.confirmed
        claim.verified_by = actor
        if req.settled_quote:
            claim.settled_quote = req.settled_quote
        log_claim_verification(
            claim,
            level="claim",
            actor=actor,
            action="confirm_claim",
            verdict="passed",
            summary=f"Claim fact settled by {actor.title()}",
            details={"quote": req.settled_quote} if req.settled_quote else {},
        )
    elif req.action == "edit" and req.edited_text:
        claim.text = req.edited_text
        claim.verification = VerificationState.edited
        claim.verified_by = actor
        claim.draft_approved = False
        claim.draft_text = None
        if req.settled_quote:
            claim.settled_quote = req.settled_quote
        log_claim_verification(
            claim,
            level="claim",
            actor=actor,
            action="edit_claim",
            verdict="passed",
            summary=f"Claim text edited by {actor.title()}",
            details={"edited_text": req.edited_text},
        )
    elif req.action == "skip":
        claim.verification = VerificationState.skipped
        claim.verified_by = actor
        claim.draft_approved = False
        claim.draft_text = None
        log_claim_verification(
            claim,
            level="claim",
            actor=actor,
            action="skip_claim",
            verdict="rejected",
            summary=f"Claim skipped by {actor.title()}",
        )
    elif req.action == "approve_draft":
        source = next((source for source in profile.sources if source.url == claim.source_url), None)
        if source is None or not (source.human_verified or source.identity_status == "confirmed"):
            raise HTTPException(400, "Draft claims require a verified source")
        if claim.verification in {VerificationState.unverified, VerificationState.skipped}:
            claim.verification = VerificationState.confirmed
            claim.verified_by = actor
        claim.draft_approved = True
        claim.draft_text = req.edited_text or claim.text
        claim.draft_approved_by = actor
        if req.settled_quote:
            claim.settled_quote = req.settled_quote
        log_claim_verification(
            claim,
            level="draft",
            actor=actor,
            action="approve_draft",
            verdict="passed",
            summary=f"Claim approved for draft by {actor.title()}",
            details={"draft_text": claim.draft_text},
        )
    elif req.action == "edit_draft_text" and req.edited_text:
        source = next((source for source in profile.sources if source.url == claim.source_url), None)
        if source is None or not (source.human_verified or source.identity_status == "confirmed"):
            raise HTTPException(400, "Draft claims require a verified source")
        if claim.verification in {VerificationState.unverified, VerificationState.skipped}:
            claim.verification = VerificationState.confirmed
            claim.verified_by = actor
        claim.draft_text = req.edited_text
        claim.draft_approved = True
        claim.draft_approved_by = actor
        log_claim_verification(
            claim,
            level="draft",
            actor=actor,
            action="edit_draft_text",
            verdict="passed",
            summary=f"Draft text updated by {actor.title()}",
            details={"draft_text": req.edited_text},
        )
    elif req.action == "remove_draft":
        claim.draft_approved = False
        claim.draft_text = None
        log_claim_verification(
            claim,
            level="draft",
            actor=actor,
            action="remove_draft",
            verdict="rejected",
            summary=f"Draft approval revoked by {actor.title()}",
        )
    else:
        raise HTTPException(400, f"Unsupported claim action: {req.action}")

    store._save_session(profile)
    return {"claim": claim.model_dump()}


@research_router.post("/research/batch-verify-claims")
def batch_verify_claims(name: str, req: BatchVerifyClaimsRequest) -> dict:
    """Batch approve, confirm, or skip unreviewed claims."""
    profile = store._get_profile(name)
    sources_by_url = {normalize_url(s.url): s for s in profile.sources}
    count = 0
    actor = req.actor or "human"

    if req.action == "approve_all_usable":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                source = sources_by_url.get(normalize_url(claim.source_url)) if claim.source_url else None
                if (
                    source
                    and (source.human_verified or source.identity_status == "confirmed")
                    and source.reliability != SourceReliability.unreliable
                    and source.relevance_flag != "likely_wrong"
                    and not (source.liveness == "dead" and not source.archive_url)
                ):
                    claim.verification = VerificationState.confirmed
                    claim.verified_by = actor
                    claim.draft_approved = True
                    claim.draft_text = claim.text
                    claim.draft_approved_by = actor
                    log_claim_verification(claim, "draft", actor, "batch_approve", "passed", f"Batch approved by {actor.title()}")
                    count += 1
    elif req.action == "confirm_all":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                claim.verification = VerificationState.confirmed
                claim.verified_by = actor
                log_claim_verification(claim, "claim", actor, "batch_confirm", "passed", f"Batch confirmed by {actor.title()}")
                count += 1
    elif req.action == "skip_unverified":
        for claim in profile.claims:
            if claim.verification == VerificationState.unverified:
                claim.verification = VerificationState.skipped
                claim.verified_by = actor
                claim.draft_approved = False
                claim.draft_text = None
                log_claim_verification(claim, "claim", actor, "batch_skip", "rejected", f"Batch skipped by {actor.title()}")
                count += 1
    else:
        raise HTTPException(400, f"Unsupported batch action: {req.action}")

    store._save_session(profile)
    return {"profile": profile.model_dump(), "updated_count": count}


@research_router.post("/research/add-source-paste")
def add_source_paste(req: AddSourcePaste) -> dict:
    """User pasted text from a blocked page (or typed from a screenshot/PDF)."""
    profile = store._get_profile(req.profile_name)
    source = fetch_url_source_with_paste(req.url, req.pasted_text)
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
    source.human_verified = True
    new_claims = extract_claims(profile, [source], store.llm())
    profile.sources.append(source)
    profile.claims.extend(new_claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/crawl")
def deep_crawl(req: CrawlRequest) -> dict:
    """Start from seed URLs and crawl outward — follow links to find more sources."""
    profile = store._get_profile(req.profile_name)
    keywords = req.keywords or [profile.field or "", profile.affiliation or ""]
    keywords = [k for k in keywords if k]

    graph = crawl(
        seed_urls=req.seed_urls,
        person_name=profile.name,
        keywords=keywords,
        max_nodes=req.max_nodes,
        max_depth=req.max_depth,
    )

    new_sources = graph.to_sources(None)
    new_sources = classify_sources(new_sources, store.llm())

    # Only keep sources that mention the person and are not already known or discarded
    excluded = get_known_and_discarded_canonical_urls(profile)

    relevant = []
    for s in new_sources:
        c_url = canonical_url(s.url)
        if c_url in excluded:
            continue
        v_res = verify_name_in_content(
            profile.name,
            s.snippet or "",
            title=s.title or "",
            field=profile.field,
            affiliation=profile.affiliation,
            nationality=profile.nationality,
        )
        if not v_res.matched or v_res.homonym_risk:
            record_discarded(
                profile,
                s.url,
                reason="homonym_risk" if v_res.homonym_risk else "no_name_match",
                title=s.title,
                snippet=s.snippet,
                name_checked=profile.name,
            )
            excluded.add(c_url)
        elif _namesake_check(profile, s.snippet or "", s.title or "")[0] == "known_conflict":
            record_discarded(profile, s.url, reason="namesake", title=s.title, snippet=s.snippet, name_checked=profile.name)
            excluded.add(c_url)
        elif graph.relevance_hits.get(s.url, 0) > 0:
            if v_res.identity_strength == "weak":
                s.identity_status = "suspect"
                s.identity_note = "initials/surname-only name match — confirm authorship/affiliation before extraction"
            relevant.append(s)
            excluded.add(c_url)

    new_claims = []
    profile.sources.extend(relevant)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    return {
        "nodes_crawled": len(graph.nodes),
        "relevant_sources": len(relevant),
        "new_claims": len(new_claims),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in relevant],
    }


@research_router.post("/research/targeted-search")
def targeted_search_endpoint(req: TargetedSearchRequest) -> dict:
    """Search for sources likely to fill a specific Wikipedia slot."""
    profile = store._get_profile(req.profile_name)
    sources = targeted_slot_search(
        person_name=profile.name,
        slot=req.slot,
        field=profile.field,
        affiliation=profile.affiliation,
        hint=req.hint,
    )
    # Deduplicate against existing active and discarded sources
    excluded = get_known_and_discarded_canonical_urls(profile)

    candidate_filtered = []
    for s in sources:
        c_url = canonical_url(s.url)
        if c_url in excluded:
            continue
        v_res = verify_name_in_content(
            profile.name,
            s.snippet or "",
            title=s.title or "",
            field=profile.field,
            affiliation=profile.affiliation,
            nationality=profile.nationality,
        )
        if not v_res.matched or v_res.homonym_risk:
            record_discarded(
                profile,
                s.url,
                reason="homonym_risk" if v_res.homonym_risk else "no_name_match",
                title=s.title,
                snippet=s.snippet,
                name_checked=profile.name,
            )
            excluded.add(c_url)
        elif _namesake_check(profile, s.snippet or "", s.title or "")[0] == "known_conflict":
            record_discarded(profile, s.url, reason="namesake", title=s.title, snippet=s.snippet, name_checked=profile.name)
            excluded.add(c_url)
        else:
            if v_res.identity_strength == "weak":
                s.identity_status = "suspect"
                s.identity_note = "initials/surname-only name match — confirm authorship/affiliation before extraction"
            candidate_filtered.append(s)
            excluded.add(c_url)

    new_sources = _enrich_and_flag_sources(candidate_filtered, profile.name, profile.field or "", profile.affiliation or "")
    accepted = []
    for s in new_sources:
        if s.reliability.value in ("self_published", "unreliable"):
            record_discarded(profile, s.url, reason="unreliable", title=s.title, snippet=s.snippet, name_checked=profile.name)
        elif s.relevance_flag != "relevant":
            record_discarded(profile, s.url, reason="off_topic", title=s.title, snippet=s.snippet, name_checked=profile.name)
        else:
            accepted.append(s)
    new_sources = accepted

    new_claims = []
    profile.sources.extend(new_sources)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    return {
        "sources": [s.model_dump() for s in new_sources],
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/auto-enrich")
def auto_enrich_endpoint(body: dict) -> dict:
    """Autonomous discovery loop — inspects missing slots and recursively iterates search queries."""
    profile_name = body["profile_name"]
    profile = store._get_profile(profile_name)
    missing = profile.missing_slots or find_missing_slots(profile, profile.claims)

    excluded = get_known_and_discarded_canonical_urls(profile)

    added_sources = []
    added_claims = []
    max_slots = 8
    max_sources = 15

    # Iterate through missing slots and execute targeted multi-query search
    for slot in missing[:max_slots]:
        if len(added_sources) >= max_sources:
            break
        candidate_sources = targeted_slot_search(
            person_name=profile.name,
            slot=slot,
            field=profile.field,
            affiliation=profile.affiliation,
        )
        candidates_to_process = []
        for s in candidate_sources:
            c_url = canonical_url(s.url)
            if c_url in excluded:
                continue
            v_res = verify_name_in_content(
                profile.name,
                s.snippet or "",
                title=s.title or "",
                field=profile.field,
                affiliation=profile.affiliation,
                nationality=profile.nationality,
            )
            if not v_res.matched or v_res.homonym_risk:
                record_discarded(
                    profile,
                    s.url,
                    reason="homonym_risk" if v_res.homonym_risk else "no_name_match",
                    title=s.title,
                    snippet=s.snippet,
                    name_checked=profile.name,
                )
                excluded.add(c_url)
            elif _namesake_check(profile, s.snippet or "", s.title or "", v_res.variant)[0] == "known_conflict":
                record_discarded(profile, s.url, reason="namesake", title=s.title, snippet=s.snippet, name_checked=profile.name)
                excluded.add(c_url)
            else:
                if v_res.identity_strength == "weak":
                    s.identity_status = "suspect"
                    s.identity_note = "initials/surname-only name match — confirm authorship/affiliation before extraction"
                candidates_to_process.append(s)
                excluded.add(c_url)

        new_sources = candidates_to_process[: max_sources - len(added_sources)]
        if new_sources:
            new_sources = _enrich_and_flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
            accepted = []
            for s in new_sources:
                if s.reliability.value in ("self_published", "unreliable"):
                    record_discarded(profile, s.url, reason="unreliable", title=s.title, snippet=s.snippet, name_checked=profile.name)
                else:
                    accepted.append(s)
            new_sources = accepted

            new_claims = extract_claims(profile, new_sources, store.llm())

            profile.sources.extend(new_sources)
            profile.claims.extend(new_claims)
            added_sources.extend(new_sources)
            added_claims.extend(new_claims)

    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    return {
        "ok": True,
        "added_source_count": len(added_sources),
        "added_claim_count": len(added_claims),
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump(),
    }


@research_router.post("/research/article-proposal")
def article_proposal(body: dict) -> dict:
    """Existing-article mode: compare confirmed claims against the live article
    and emit a structured edit proposal (covered vs candidate additions)."""
    from adapters.wiki.article_compare import build_article_proposal, fetch_article_text, title_from_url

    profile = store._get_profile(body["profile_name"])
    sid = store._ensure_session_id(profile)
    status = store._wiki_statuses.get(sid) or store._wiki_statuses.get(profile.name, {})
    if status.get("status") != "exists":
        raise HTTPException(400, "Article comparison is only available when an article already exists.")
    url = status.get("url")
    if not url:
        raise HTTPException(400, "No article URL recorded for this session.")

    title = title_from_url(url)
    try:
        article_text = fetch_article_text(title)
    except Exception as exc:
        raise HTTPException(502, f"Could not fetch the live article: {exc}")

    proposal = build_article_proposal(profile, title, url, article_text)
    return {"proposal": proposal.model_dump()}

@research_router.get("/session/namesakes")
def list_namesakes(profile_name: str) -> dict:
    profile = store._get_profile(profile_name)
    return {"namesakes": [n.model_dump() for n in profile.known_namesakes]}


@research_router.get("/session/{name}")
def get_session(name: str) -> dict:
    return {"profile": store._get_profile(name).model_dump()}


@research_router.post("/research/source/verify")
def verify_source(body: dict) -> dict:
    """Mark a source as verified (by human or agent). On verify, extract claims from it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    verified = body.get("verified", True)
    actor = body.get("actor", "human")
    source = next((s for s in profile.sources if s.url == url), None)
    if not source:
        return {"ok": True, "new_claims": [], "missing_slots": profile.missing_slots}

    new_claims: list = []
    if verified:
        from datetime import datetime, timezone
        source.confirmed_for_extraction_by = actor
        source.confirmed_for_extraction_at = datetime.now(timezone.utc).isoformat()
        if actor == "human":
            source.human_verified = True

        # L1: Liveness + Wayback fallback at the moment of confirmation.
        from engine.fetcher import check_liveness
        source.liveness, source.archive_url = check_liveness(url)
        liveness_verdict = "passed" if source.liveness == "alive" else ("warning" if source.archive_url else "rejected")
        log_source_verification(
            source,
            level="liveness",
            actor=actor,
            action="check_liveness",
            verdict=liveness_verdict,
            summary=f"Link accessibility checked ({source.liveness}) by {actor.title()}",
            details={"liveness": source.liveness, "archive_url": source.archive_url},
        )

        # L2: Identity confirmation & extraction authorization
        source.identity_status = "confirmed"
        source.identity_by = actor
        log_source_verification(
            source,
            level="identity",
            actor=actor,
            action="confirm_person_and_extract",
            verdict="passed",
            summary=f"Identity confirmed and claim extraction authorized by {actor.title()}",
            details={"title": source.title, "publisher": source.publisher},
        )
    else:
        source.human_verified = False
        source.identity_status = "unverified"
        source.confirmed_for_extraction_by = None
        source.confirmed_for_extraction_at = None
        log_source_verification(
            source,
            level="identity",
            actor=actor,
            action="unverify_source",
            verdict="warning",
            summary=f"Source unverified by {actor.title()}",
        )

    if verified and source.relevance_flag == "likely_wrong":
        source.extraction_status = "likely_wrong"
        source.extraction_note = "Source flagged as likely a different person. No claims extracted."
    elif verified:
        norm_target = normalize_url(url)
        new_claims = []
        existing_for_url = [c for c in profile.claims if c.source_url and normalize_url(c.source_url) == norm_target]
        if not existing_for_url:
            from engine.llm import StubProvider, NullProvider, LocalProvider
            llm_inst = store.llm()
            extracted = extract_claims(profile, [source], llm_inst)
            if extracted:
                for c in extracted:
                    c.verified_by = actor
                    log_claim_verification(
                        c,
                        level="claim",
                        actor=actor,
                        action="auto_extracted",
                        verdict="unverified",
                        summary=f"Claim auto-extracted from verified source by {actor.title()}",
                    )
                profile.claims.extend(extracted)
                profile.missing_slots = find_missing_slots(profile, profile.claims)
                new_claims = extracted
                source.extraction_status = "extracted"
                source.extraction_note = f"{len(extracted)} claims extracted from this source."
            else:
                if isinstance(llm_inst, (StubProvider, NullProvider, LocalProvider)):
                    source.extraction_status = "stub_mode"
                    source.extraction_note = "LLM in rule/stub mode — to prevent fabrication, claims are not auto-extracted. Use '+ Add Sourced Claim' to add facts from this source."
                elif not source.snippet and (not source.title or source.title == source.url):
                    source.extraction_status = "thin_content"
                    source.extraction_note = "Page content was too short or lacked verifiable biographical statements."
                else:
                    source.extraction_status = "redundant"
                    source.extraction_note = "No novel claims found. The facts in this source are already backed by other verified sources in your session."
        else:
            new_claims = existing_for_url
            source.extraction_status = "extracted"
            source.extraction_note = f"Source verified ({len(existing_for_url)} claims in session)."

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "ok": True,
        "source": source.model_dump(),
        "new_claims": [c.model_dump() for c in new_claims],
        "missing_slots": profile.missing_slots,
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/source/verify-level")
def verify_source_level(req: VerifySourceLevelRequest) -> dict:
    """Explicitly verify or update a single verification level (L1 Liveness, L2 Identity, L3 Provenance)."""
    profile = store._get_profile(req.profile_name)
    source = next((s for s in profile.sources if s.url == req.url), None)
    if not source:
        raise HTTPException(404, f"Source not found in this session: {req.url}")

    if req.level == "liveness":
        if req.status:
            source.liveness = req.status
        else:
            from engine.fetcher import check_liveness
            source.liveness, source.archive_url = check_liveness(source.url)
        verdict = "passed" if source.liveness == "alive" else ("warning" if source.archive_url else "rejected")
        log_source_verification(
            source,
            level="liveness",
            actor=req.actor,
            action="verify_liveness",
            verdict=verdict,
            summary=f"Liveness verified as '{source.liveness}' by {req.actor.title()}" + (f": {req.note}" if req.note else ""),
            details={"liveness": source.liveness, "archive_url": source.archive_url, "note": req.note},
        )
    elif req.level == "identity":
        status = req.status or "confirmed"
        source.identity_status = status
        source.identity_note = req.note
        if status == "wrong_person":
            source.relevance_flag = "likely_wrong"
            source.human_verified = False
            log_source_verification(
                source,
                level="identity",
                actor=req.actor,
                action="reject_person",
                verdict="rejected",
                summary=f"Subject rejected as wrong person / namesake by {req.actor.title()}" + (f": {req.note}" if req.note else ""),
                details={"reason": req.note},
            )
        elif status == "suspect":
            # suspect keeps human_verified unraised: needs a human re-look before extraction
            source.relevance_flag = "uncertain" if source.relevance_flag == "likely_wrong" else source.relevance_flag
            log_source_verification(
                source,
                level="identity",
                actor=req.actor,
                action="flag_suspect_identity",
                verdict="warning",
                summary=f"Identity flagged suspect by {req.actor.title()}" + (f": {req.note}" if req.note else ""),
                details={"reason": req.note},
            )
        else:
            from datetime import datetime, timezone
            source.confirmed_for_extraction_by = req.actor
            source.confirmed_for_extraction_at = datetime.now(timezone.utc).isoformat()
            if req.actor == "human":
                source.human_verified = True
            source.identity_status = "confirmed"
            source.relevance_flag = "relevant" if source.relevance_flag == "likely_wrong" else source.relevance_flag
            log_source_verification(
                source,
                level="identity",
                actor=req.actor,
                action="confirm_person_and_extract",
                verdict="passed",
                summary=f"Subject identity confirmed and claim extraction authorized by {req.actor.title()}" + (f": {req.note}" if req.note else ""),
                details={"note": req.note},
            )
    elif req.level == "provenance":
        if req.coverage_depth:
            source.coverage_depth = req.coverage_depth
        if req.editorial_origin:
            source.editorial_origin = req.editorial_origin
        if req.note:
            source.research_notes = req.note
        log_source_verification(
            source,
            level="provenance",
            actor=req.actor,
            action="assess_provenance",
            verdict="passed",
            summary=f"Provenance assessed by {req.actor.title()}",
            details={"coverage_depth": source.coverage_depth, "editorial_origin": source.editorial_origin},
        )
    elif req.level == "all":
        source.human_verified = True
        source.identity_status = "confirmed"
        if req.coverage_depth:
            source.coverage_depth = req.coverage_depth
        from engine.fetcher import check_liveness
        source.liveness, source.archive_url = check_liveness(source.url)
        log_source_verification(
            source,
            level="identity",
            actor=req.actor,
            action="verify_all_levels",
            verdict="passed",
            summary=f"Full source verification recorded by {req.actor.title()}",
        )

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {"ok": True, "source": source.model_dump(), "notability": profile.notability.model_dump() if profile.notability else None}


@research_router.get("/research/verification-summary")
def get_verification_summary(profile_name: str) -> dict:
    """Return a multi-level breakdown of verification health and agent/human actor attribution."""
    profile = store._get_profile(profile_name)
    total_sources = len(profile.sources)
    total_claims = len(profile.claims)

    l1_alive = sum(1 for s in profile.sources if getattr(s, "liveness", "unknown") == "alive")
    l1_dead = sum(1 for s in profile.sources if getattr(s, "liveness", "unknown") == "dead")
    l1_blocked = sum(1 for s in profile.sources if getattr(s, "liveness", "unknown") == "blocked")
    l1_agent = sum(1 for s in profile.sources if getattr(s, "liveness_by", None) == "agent")
    l1_human = sum(1 for s in profile.sources if getattr(s, "liveness_by", None) == "human")

    l2_confirmed = sum(1 for s in profile.sources if getattr(s, "identity_status", "unverified") == "confirmed" or s.human_verified)
    l2_suspect = sum(1 for s in profile.sources if getattr(s, "identity_status", "unverified") in {"suspect", "wrong_person"} or getattr(s, "relevance_flag", "") == "likely_wrong")
    l2_unverified = max(0, total_sources - l2_confirmed - l2_suspect)
    l2_agent = sum(1 for s in profile.sources if getattr(s, "identity_by", None) == "agent")
    l2_human = sum(1 for s in profile.sources if getattr(s, "identity_by", None) == "human" or (s.human_verified and not getattr(s, "identity_by", None)))

    l3_significant = sum(1 for s in profile.sources if getattr(s, "coverage_depth", "unassessed") == "significant")
    l3_passing = sum(1 for s in profile.sources if getattr(s, "coverage_depth", "unassessed") == "passing_mention")
    l3_independent = sum(1 for s in profile.sources if getattr(s, "is_independent", False) and getattr(s, "provenance_category", "") == "independent_secondary")

    l4_settled = sum(1 for c in profile.claims if c.verification in {VerificationState.confirmed, VerificationState.edited})
    l4_unverified = sum(1 for c in profile.claims if c.verification == VerificationState.unverified)
    l4_skipped = sum(1 for c in profile.claims if c.verification == VerificationState.skipped)
    l4_agent = sum(1 for c in profile.claims if getattr(c, "verified_by", None) == "agent")
    l4_human = sum(1 for c in profile.claims if getattr(c, "verified_by", None) == "human")

    l5_approved = sum(1 for c in profile.claims if c.draft_approved)
    l5_agent = sum(1 for c in profile.claims if c.draft_approved and getattr(c, "draft_approved_by", None) == "agent")
    l5_human = sum(1 for c in profile.claims if c.draft_approved and getattr(c, "draft_approved_by", None) != "agent")

    total_agent_events = 0
    total_human_events = 0
    for s in profile.sources:
        for entry in getattr(s, "verification_trail", []) or []:
            if getattr(entry, "actor", None) == "agent":
                total_agent_events += 1
            elif getattr(entry, "actor", None) == "human":
                total_human_events += 1
    for c in profile.claims:
        for entry in getattr(c, "verification_trail", []) or []:
            if getattr(entry, "actor", None) == "agent":
                total_agent_events += 1
            elif getattr(entry, "actor", None) == "human":
                total_human_events += 1

    return {
        "levels": {
            "l1_liveness": {
                "total": total_sources,
                "alive": l1_alive,
                "dead": l1_dead,
                "blocked": l1_blocked,
                "checked_by_agent": l1_agent,
                "checked_by_human": l1_human,
            },
            "l2_identity": {
                "total": total_sources,
                "confirmed": l2_confirmed,
                "suspect": l2_suspect,
                "unverified": l2_unverified,
                "verified_by_agent": l2_agent,
                "verified_by_human": l2_human,
            },
            "l3_provenance": {
                "total": total_sources,
                "significant": l3_significant,
                "passing_mention": l3_passing,
                "independent_secondary": l3_independent,
            },
            "l4_claims": {
                "total": total_claims,
                "settled": l4_settled,
                "unverified": l4_unverified,
                "skipped": l4_skipped,
                "verified_by_agent": l4_agent,
                "verified_by_human": l4_human,
            },
            "l5_draft": {
                "total_approved": l5_approved,
                "approved_by_agent": l5_agent,
                "approved_by_human": l5_human,
            },
        },
        "audit_events": {
            "agent_actions": total_agent_events,
            "human_actions": total_human_events,
        },
    }


@research_router.post("/research/source/reject")
def reject_source(body: dict) -> dict:
    """Remove a source and all claims extracted from it and register in discarded registry."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    c_url = canonical_url(url)
    matching = [s for s in profile.sources if canonical_url(s.url) == c_url or s.url == url]
    title = matching[0].title if matching else ""
    snippet = matching[0].snippet if matching else ""

    profile.sources = [s for s in profile.sources if s.url != url and canonical_url(s.url) != c_url]
    removed = [c for c in profile.claims if c.source_url == url or canonical_url(c.source_url or "") == c_url]
    profile.claims = [c for c in profile.claims if c.source_url != url and canonical_url(c.source_url or "") != c_url]

    record_discarded(
        profile,
        url,
        reason=body.get("reason", "user_rejected"),
        title=title,
        snippet=snippet,
        name_checked=profile.name,
    )
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "removed_claim_count": len(removed),
        "notability": profile.notability.model_dump(),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
    }


@research_router.post("/research/skip-suggestion")
def skip_suggestion(body: dict) -> dict:
    """Record a suggestion as skipped so discovery stops re-offering it."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    if url not in profile.skipped_sources:
        profile.skipped_sources.append(url)
    record_discarded(
        profile,
        url,
        reason="user_skipped",
        title=body.get("title", ""),
        snippet=body.get("snippet", ""),
        name_checked=profile.name,
    )
    store._save_session(profile)
    return {"ok": True}


@research_router.get("/research/discarded-sources")
def get_discarded_sources_endpoint(profile_name: str, reason: str | None = None) -> dict:
    """Return all discarded sources for human or agent audit and recovery."""
    profile = store._get_profile(profile_name)
    discarded = profile.discarded_sources
    if reason:
        discarded = [d for d in discarded if d.reason == reason]
    return {
        "count": len(discarded),
        "discarded": [d.model_dump() for d in discarded],
    }


@research_router.post("/research/source/recover-discarded")
def recover_discarded_endpoint(body: dict) -> dict:
    """Recover a previously discarded source so it can be re-evaluated or accepted."""
    profile = store._get_profile(body["profile_name"])
    url = body["url"]
    recovered = recover_discarded(profile, url)
    store._save_session(profile)
    return {
        "ok": recovered is not None,
        "recovered": recovered.model_dump() if recovered else None,
    }


@research_router.get("/research/lifecycle-audit")
def get_lifecycle_audit_endpoint(profile_name: str) -> dict:
    """Run comprehensive lifecycle audit across all 4 research and drafting stages."""
    from dataclasses import asdict
    from engine.lifecycle_audit import audit_full_lifecycle
    profile = store._get_profile(profile_name)
    audit = audit_full_lifecycle(profile)
    return asdict(audit)


@research_router.get("/research/mobile-bridge-status")
def get_mobile_bridge_status_endpoint() -> dict:
    """Return status of OpenScrape mobile browser bridge (Tailnet port 38765)."""
    from engine.mobile_bridge import is_mobile_bridge_available, get_mobile_client
    online = is_mobile_bridge_available()
    details = None
    if online:
        client = get_mobile_client()
        if client:
            try:
                details = client.get_status()
            except Exception:
                pass
    return {
        "online": online,
        "details": details,
    }


@research_router.post("/research/find-researcher-ids")
def find_researcher_ids_endpoint(req: FindIdsRequest) -> dict:
    """Search for ORCID, Google Scholar, Scopus, ResearchGate IDs and validate ORCID."""
    from engine.researcher_ids import search_researcher_ids, validate_orcid
    profile = store._get_profile(req.profile_name)
    found = search_researcher_ids(profile.name, profile.field, profile.affiliation)
    for id_type, id_val in found.items():
        profile.researcher_ids.setdefault(id_type, id_val)

    # ORCID candidates are cheap to validate and unsafe to retain on a name hit
    # alone: coauthors and namesakes commonly appear in the same search results.
    orcid_id = profile.researcher_ids.get("orcid")
    if orcid_id and not profile.confirmed_ids.get("orcid"):
        valid = validate_orcid(orcid_id, profile.name, profile.affiliation)
        profile.confirmed_ids["orcid"] = valid
        if not valid:
            profile.researcher_ids.pop("orcid", None)

    store._save_session(profile)
    return {
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@research_router.post("/research/refresh-papers")
def refresh_papers_endpoint(req: RefreshPapersRequest) -> dict:
    """Re-fetch publications from ORCID or Semantic Scholar for a confirmed ID."""
    from engine.researcher_ids import fetch_orcid_works, fetch_s2_author_papers, validate_orcid
    profile = store._get_profile(req.profile_name)

    if req.confirm:
        if req.id_type == "orcid" and not validate_orcid(req.id_value, profile.name, profile.affiliation):
            raise HTTPException(400, "ORCID does not match the subject name and affiliation")
        profile.researcher_ids[req.id_type] = req.id_value
        profile.confirmed_ids[req.id_type] = True

    if req.id_type == "orcid":
        new_sources = fetch_orcid_works(req.id_value)
    elif req.id_type == "semantic_scholar":
        new_sources = fetch_s2_author_papers(req.id_value, limit=20)
    else:
        raise HTTPException(400, f"Unsupported id_type: {req.id_type}")

    existing_urls = {s.url for s in profile.sources}
    new_sources = [s for s in new_sources if s.url not in existing_urls]
    for s in new_sources:
        s.human_verified = True
    new_sources = _enrich_and_flag_sources(new_sources, profile.name, profile.field or "", profile.affiliation or "")
    new_claims = extract_claims(profile, new_sources, store.llm())
    profile.sources.extend(new_sources)
    profile.claims.extend(new_claims)
    profile.missing_slots = find_missing_slots(profile, profile.claims)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    return {
        "new_source_count": len(new_sources),
        "new_claim_count": len(new_claims),
        "sources": [s.model_dump() for s in profile.sources],
        "claims": [c.model_dump() for c in profile.claims],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@research_router.post("/research/fetch-from-browser")
def fetch_from_browser(body: dict) -> dict:
    """Pull the current page from browser_server and add it as a source."""
    profile = store._get_profile(body["profile_name"])

    try:
        from browser_server import _dispatch, _running
        if not _running:
            raise HTTPException(503, "Browser server is not running")
        data = _dispatch("content")
    except Exception as e:
        raise HTTPException(503, f"Browser server error: {e}")

    url = data.get("url", "")
    text = data.get("text", "")
    if not url or url in ("about:blank", ""):
        raise HTTPException(400, "Browser has no page loaded yet")

    if any(s.url == url for s in profile.sources):
        raise HTTPException(400, "This source is already in your list.")

    source = fetch_url_source_with_paste(url, text)
    [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")

    profile.sources.append(source)
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)

    return {
        "source": source.model_dump(),
        "blocked": False,
        "sent_to_browser": False,
        "new_claims": [],
        "notability": profile.notability.model_dump(),
        "researcher_ids": profile.researcher_ids,
        "confirmed_ids": profile.confirmed_ids,
    }


@research_router.post("/research/fetch-blocked")
def fetch_blocked(body: dict) -> dict:
    """Auto-fetch blocked sources through the remote browser.

    Walks sources whose liveness is 'blocked', navigating the companion browser
    to each and capturing the rendered page. Stops at the first bot wall so the
    human can solve it in the companion browser, then resume. Playwright does
    the navigation and capture; a genuine CAPTCHA is the only thing that pauses.
    """
    profile = store._get_profile(body["profile_name"])
    try:
        from browser_server import _dispatch, _running, looks_like_wall
        if not _running:
            raise HTTPException(503, "Remote browser is not running — open the companion browser first.")
    except ImportError:
        raise HTTPException(503, "Remote browser is not available")

    targets = [s for s in profile.sources if s.liveness == "blocked"]
    fetched, walls = [], []
    for source in targets:
        _dispatch("navigate", url=source.url)
        data = _dispatch("content")
        text = (data.get("text") or "").strip()
        if len(text) < 200 or looks_like_wall(text):
            walls.append(source.url)
            break
        source.snippet = text[:400]
        source.liveness = "alive"
        source.fetched_by = "browser"
        [source] = _enrich_and_flag_sources([source], profile.name, profile.field or "", profile.affiliation or "")
        fetched.append(source.url)

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "fetched": fetched,
        "walls": walls,
        "profile": profile.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
    }


@research_router.post("/research/suggest")
def suggest_urls(body: dict) -> dict:
    """Return a ranked queue of URL suggestions based on what the profile is missing."""
    from engine.suggester import suggest_next_urls
    from engine.models import UrlSuggestion
    profile = store._get_profile(body["profile_name"])
    suggestions = suggest_next_urls(profile, max_results=body.get("max_results", 8))
    validated = [UrlSuggestion(**s).model_dump() for s in suggestions]
    return {"suggestions": validated}



@research_router.post("/research/source/assess")
def assess_source(req: AssessSourceRequest) -> dict:
    """Persist coverage depth, editorial origin, and durable research notes.

    Assessment affects the informational notability signal, never whether a
    confirmed claim remains available in the research dossier.
    """
    profile = store._get_profile(req.profile_name)
    source = next((item for item in profile.sources if item.url == req.url), None)
    if source is None:
        raise HTTPException(404, "Source not found in this session")
    if req.coverage_depth == "significant" and not (source.human_verified or getattr(source, "identity_status", "") == "confirmed"):
        raise HTTPException(400, "Verify the source before marking significant coverage")

    actor = req.actor or "human"
    source.coverage_depth = req.coverage_depth
    source.editorial_origin = (req.editorial_origin or "").strip() or None
    source.research_notes = req.research_notes.strip()

    log_source_verification(
        source,
        level="provenance",
        actor=actor,
        action="assess_provenance",
        verdict="passed",
        summary=f"Coverage depth assessed as '{req.coverage_depth}' by {actor.title()}",
        details={
            "coverage_depth": req.coverage_depth,
            "editorial_origin": source.editorial_origin,
            "notes": source.research_notes,
        },
    )

    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "source": source.model_dump(),
        "notability": profile.notability.model_dump() if profile.notability else None,
    }



@research_router.post("/session/namesakes")
def add_namesake(req: AddNamesakeRequest) -> dict:
    """Add a session-scoped namesake signature. Ingest then auto-screens against it."""
    import uuid as _uuid
    profile = store._get_profile(req.profile_name)
    from datetime import datetime, timezone
    namesake = KnownNamesake(
        namesake_id=req.namesake_id or f"ns-{_uuid.uuid4().hex[:8]}",
        display_name=req.display_name.strip(),
        signature_terms=[t.strip() for t in req.signature_terms if t.strip()],
        distinguishing_traits=[t.strip() for t in req.distinguishing_traits if t.strip()],
        notes=req.notes,
        created_by=req.actor or "human",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    if any(ns.namesake_id == namesake.namesake_id for ns in profile.known_namesakes):
        raise HTTPException(409, f"Namesake {namesake.namesake_id} already exists")
    profile.known_namesakes.append(namesake)
    store._save_session(profile)
    return {"ok": True, "namesakes": [n.model_dump() for n in profile.known_namesakes]}


@research_router.delete("/session/namesakes/{namesake_id}")
def delete_namesake(namesake_id: str, profile_name: str) -> dict:
    profile = store._get_profile(profile_name)
    before = len(profile.known_namesakes)
    profile.known_namesakes = [n for n in profile.known_namesakes if n.namesake_id != namesake_id]
    if len(profile.known_namesakes) == before:
        raise HTTPException(404, f"Namesake {namesake_id} not found")
    store._save_session(profile)
    return {"ok": True, "namesakes": [n.model_dump() for n in profile.known_namesakes]}


@research_router.get("/session/namesakes")
def list_namesakes(profile_name: str) -> dict:
    profile = store._get_profile(profile_name)
    return {"namesakes": [n.model_dump() for n in profile.known_namesakes]}


@research_router.get("/research/claim-clusters")
def get_claim_clusters(profile_name: str) -> dict:
    """Fact clusters: one fact, every supporting link, ranked best-citation first."""
    from engine.claim_selection import build_claim_clusters
    profile = store._get_profile(profile_name)
    clusters = build_claim_clusters(profile)
    return {
        "clusters": clusters,
        "multi_link": sum(1 for c in clusters if c["link_count"] > 1),
        "total_facts": len(clusters),
    }


@research_router.post("/research/claim-clusters/select-source")
def select_cluster_source(body: dict) -> dict:
    """Rebind one claim to a better-ranked source for the same fact.

    Honesty invariant: rebinding invalidates verification and draft approval for
    that claim (the settled quote belonged to the previous source), so the fact
    must be re-verified before it can enter the draft again.
    """
    profile = store._get_profile(body["profile_name"])
    try:
        idx = int(body["claim_index"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(400, "claim_index is required")
    if idx < 0 or idx >= len(profile.claims):
        raise HTTPException(400, "claim_index out of range")
    new_url = (body.get("source_url") or "").strip()
    if not new_url:
        raise HTTPException(400, "source_url is required")
    source = next((s for s in profile.sources if s.url == new_url), None)
    if source is None:
        raise HTTPException(404, f"Source not found in this session: {new_url}")

    claim = profile.claims[idx]
    previous_url = claim.source_url
    claim.source_url = new_url
    claim.verification = VerificationState.unverified
    claim.settled_quote = None
    claim.draft_approved = False
    claim.draft_text = None
    claim.draft_approved_by = None
    claim.verified_by = None
    log_claim_verification(
        claim,
        level="claim",
        actor=body.get("actor", "human"),
        action="rebind_source",
        verdict="warning",
        summary=f"Fact rebound to better-ranked source ({new_url[:80]}); re-verification required",
        details={"previous_source_url": previous_url, "new_source_url": new_url},
    )
    profile.notability = score_notability(profile.name, profile.sources, profile.claims)
    store._save_session(profile)
    return {
        "ok": True,
        "claim_index": idx,
        "claim": claim.model_dump(),
        "best_source_url": new_url,
    }


@research_router.post("/research/claim-clusters/select-best-all")
def select_best_all(body: dict) -> dict:
    """Upgrade every multi-link fact to its best-ranked link (dry-run by default).

    Only *upgrades* are applied: the best link must out-rank the fact's current
    source. Rebinding clears that claim's verification/approval (honesty
    invariant) so the change is visible in the review queue.
    """
    from engine.claim_selection import build_claim_clusters
    profile = store._get_profile(body["profile_name"])
    apply_changes = bool(body.get("apply"))
    clusters = build_claim_clusters(profile)
    planned: list[dict] = []
    for cluster in clusters:
        canon_idx = cluster.get("canonical_index")
        if canon_idx is None or cluster["link_count"] < 2:
            continue
        claim = profile.claims[canon_idx]
        ranked = cluster["sources"]
        if not ranked:
            continue
        best = ranked[0]
        if best["rank"] == -99.0:
            continue
        current_rank = next((r["rank"] for r in ranked if r["url"] == claim.source_url), None)
        if current_rank is not None and best["rank"] <= current_rank:
            continue
        if claim.source_url == best["url"]:
            continue
        planned.append({
            "claim_index": canon_idx,
            "fact": (cluster["canonical_text"] or "")[:120],
            "from": claim.source_url,
            "to": best["url"],
            "from_rank": current_rank,
            "to_rank": best["rank"],
        })
        if apply_changes:
            previous = claim.source_url
            claim.source_url = best["url"]
            claim.verification = VerificationState.unverified
            claim.settled_quote = None
            claim.draft_approved = False
            claim.draft_text = None
            claim.draft_approved_by = None
            claim.verified_by = None
            log_claim_verification(
                claim,
                level="claim",
                actor=body.get("actor", "human"),
                action="rebind_source_bulk",
                verdict="warning",
                summary=f"Fact auto-upgraded to best-ranked link ({best['url'][:80]}); re-verification required",
                details={"previous_source_url": previous, "new_source_url": best["url"],
                         "previous_rank": current_rank, "new_rank": best["rank"]},
            )
    if apply_changes and planned:
        profile.notability = score_notability(profile.name, profile.sources, profile.claims)
        store._save_session(profile)
    return {"ok": True, "apply": apply_changes, "planned": planned, "count": len(planned)}


@research_router.get("/research/draft-suggestions")
def get_draft_suggestions(profile_name: str, limit: int = 60) -> dict:
    """Facts ready (or nearly ready) to move into the draft, one per fact."""
    from engine.claim_selection import suggest_draft_upgrades
    profile = store._get_profile(profile_name)
    return suggest_draft_upgrades(profile, limit=max(1, min(limit, 300)))
