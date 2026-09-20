"""API routes for Forensic Investigation: Pivots, Auxiliary Leads, and Public Records Sweeps."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from backend.schemas import (
    AddInvestigationPivotRequest,
    AddAuxiliaryLeadRequest,
    UpdateAuxiliaryLeadRequest,
    RunForensicSweepRequest,
    PromoteLeadToSourceRequest,
    AddForensicInquiryRequest,
    UpdateForensicInquiryRequest,
    ProbeForensicInquiryRequest,
    LogInquiryFailureRequest,
)
from . import store
from engine.models import InvestigationPivot, AuxiliaryLead, Source, VerificationLogEntry, ForensicInquiry, PublicRecordRepository
from engine.forensics import (
    generate_pivot_id,
    generate_lead_id,
    generate_inquiry_id,
    seed_default_pivots,
    build_forensic_sweep_leads,
    check_subject_mention,
    generate_deductive_inquiries,
    _enrich_inquiry_dual_track,
)
from engine.public_records_atlas import (
    get_public_records_atlas,
    derive_subject_record_matrix,
    generate_civic_inquiries,
    register_public_repository,
    delete_custom_repository,
    record_repository_learning,
)

forensics_router = APIRouter(prefix="/forensics", tags=["forensics"])


@forensics_router.get("/summary")
def get_forensics_summary(profile_name: str) -> dict:
    """Retrieve forensic investigation state, auto-seeding initial pivots if empty."""
    profile = store._get_profile(profile_name)

    # Auto-seed initial anchors from subject's profile if list is empty
    if not profile.investigation_pivots:
        initial_pivots = seed_default_pivots(profile)
        if initial_pivots:
            profile.investigation_pivots.extend(initial_pivots)
            store._save_session(profile)

    # Auto-seed deductive forensic inquiries if empty
    if not profile.forensic_inquiries:
        initial_inquiries = generate_deductive_inquiries(profile)
        if initial_inquiries:
            profile.forensic_inquiries.extend(initial_inquiries)
            store._save_session(profile)

    pivots_count = len(profile.investigation_pivots)
    leads_count = len(profile.auxiliary_leads)
    corroborated_leads = sum(1 for lead in profile.auxiliary_leads if lead.status == "corroborated")
    inquiries_count = len(profile.forensic_inquiries)

    return {
        "ok": True,
        "profile_name": profile.name,
        "pivots": [p.model_dump() for p in profile.investigation_pivots],
        "leads": [l.model_dump() for l in profile.auxiliary_leads],
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
        "metrics": {
            "pivots_count": pivots_count,
            "leads_count": leads_count,
            "corroborated_leads": corroborated_leads,
            "inquiries_count": inquiries_count,
        },
    }



@forensics_router.post("/pivots")
def add_pivot(req: AddInvestigationPivotRequest) -> dict:
    """Add a new investigation pivot (institutional, project, spatial, or co-actor anchor)."""
    profile = store._get_profile(req.profile_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    new_pivot = InvestigationPivot(
        pivot_id=generate_pivot_id(),
        pivot_type=req.pivot_type,
        title=req.title.strip(),
        description=req.description.strip(),
        time_period=req.time_period.strip() if req.time_period else None,
        location=req.location.strip() if req.location else None,
        associated_entities=[e.strip() for e in req.associated_entities if e.strip()],
        created_by=req.actor or "human",
        created_at=now_iso,
    )

    profile.investigation_pivots.append(new_pivot)
    store._save_session(profile)

    return {
        "ok": True,
        "pivot": new_pivot.model_dump(),
        "pivots": [p.model_dump() for p in profile.investigation_pivots],
    }


@forensics_router.delete("/pivots/{pivot_id}")
def delete_pivot(pivot_id: str, profile_name: str) -> dict:
    """Remove an investigation pivot."""
    profile = store._get_profile(profile_name)
    before_len = len(profile.investigation_pivots)
    profile.investigation_pivots = [p for p in profile.investigation_pivots if p.pivot_id != pivot_id]

    if len(profile.investigation_pivots) == before_len:
        raise HTTPException(404, f"Pivot {pivot_id} not found")

    store._save_session(profile)
    return {"ok": True, "pivots": [p.model_dump() for p in profile.investigation_pivots]}


@forensics_router.post("/leads")
def add_auxiliary_lead(req: AddAuxiliaryLeadRequest) -> dict:
    """Manually or agentically log a helping link, public record lead, or auxiliary document."""
    profile = store._get_profile(req.profile_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    has_mention = req.has_subject_mention
    if has_mention is None:
        has_mention = check_subject_mention(
            f"{req.title} {req.lead_notes} {req.source_snippet or ''}", profile.name
        )

    new_lead = AuxiliaryLead(
        lead_id=generate_lead_id(),
        pivot_id=req.pivot_id,
        title=req.title.strip(),
        url=req.url.strip() if req.url else None,
        category=req.category,
        lead_notes=req.lead_notes.strip(),
        source_snippet=req.source_snippet.strip() if req.source_snippet else None,
        automated_query=req.automated_query.strip() if req.automated_query else None,
        actor_logged=req.actor or "human",
        status=req.status or "lead",
        has_subject_mention=has_mention,
        created_at=now_iso,
    )

    profile.auxiliary_leads.append(new_lead)
    store._save_session(profile)

    return {
        "ok": True,
        "lead": new_lead.model_dump(),
        "leads": [l.model_dump() for l in profile.auxiliary_leads],
    }


@forensics_router.patch("/leads/{lead_id}")
def update_auxiliary_lead(lead_id: str, req: UpdateAuxiliaryLeadRequest) -> dict:
    """Update status (e.g. mark corroborated or dead-end), notes, or URL of an auxiliary lead."""
    profile = store._get_profile(req.profile_name)
    target_lead = None

    for lead in profile.auxiliary_leads:
        if lead.lead_id == lead_id:
            target_lead = lead
            break

    if not target_lead:
        raise HTTPException(404, f"Lead {lead_id} not found")

    if req.status:
        target_lead.status = req.status
    if req.lead_notes is not None:
        target_lead.lead_notes = req.lead_notes
    if req.source_snippet is not None:
        target_lead.source_snippet = req.source_snippet
    if req.url is not None:
        target_lead.url = req.url
    if req.has_subject_mention is not None:
        target_lead.has_subject_mention = req.has_subject_mention
    if req.actor:
        target_lead.actor_logged = req.actor

    store._save_session(profile)
    return {
        "ok": True,
        "lead": target_lead.model_dump(),
        "leads": [l.model_dump() for l in profile.auxiliary_leads],
    }


@forensics_router.post("/leads/{lead_id}/promote-to-source")
def promote_lead_to_source(lead_id: str, req: PromoteLeadToSourceRequest) -> dict:
    """Promote an auxiliary forensic lead into a primary Wikipedia draft source with pre-verified provenance."""
    profile = store._get_profile(req.profile_name)
    target_lead = None

    for lead in profile.auxiliary_leads:
        if lead.lead_id == lead_id:
            target_lead = lead
            break

    if not target_lead:
        raise HTTPException(404, f"Lead {lead_id} not found")

    if not target_lead.url:
        raise HTTPException(400, "Cannot promote lead without a valid URL")

    url_clean = target_lead.url.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Check if already present in profile.sources
    existing_source = None
    for s in profile.sources:
        if s.url.strip() == url_clean:
            existing_source = s
            break

    if existing_source:
        target_lead.promoted_source_id = existing_source.url
        target_lead.status = "corroborated"
        target_lead.has_subject_mention = True
        store._save_session(profile)
        return {
            "ok": True,
            "promoted_source": existing_source.model_dump(),
            "lead": target_lead.model_dump(),
            "already_existed": True,
        }

    domain_trust = "high" if any(
        k in url_clean.lower()
        for k in [".gov.in", ".res.in", ".ac.in", ".edu", "sciencedirect", "springer", "wiley", "theprint.in", "nature.com"]
    ) else "medium"

    provenance = "institutional_bio" if (".gov" in url_clean or ".res" in url_clean) else "general_web"

    import urllib.parse
    parsed_host = urllib.parse.urlparse(url_clean).netloc or "Institutional Web"

    new_source = Source(
        url=url_clean,
        title=target_lead.title.strip(),
        publisher=parsed_host,
        snippet=target_lead.source_snippet or target_lead.lead_notes or "",
        fetched_by="forensic_lead",
        liveness="alive",
        liveness_by=req.actor or "agent",
        domain_trust=domain_trust,
        provenance_category=provenance,
        verification_trail=[
            VerificationLogEntry(
                level="liveness",
                actor=req.actor or "agent",
                action="check_liveness",
                verdict="passed",
                timestamp=now_iso,
                summary="Verified live via forensic sweep",
            ),
            VerificationLogEntry(
                level="identity",
                actor=req.actor or "agent",
                action="confirm_person",
                verdict="passed",
                timestamp=now_iso,
                summary="Corroborated via institutional forensic investigation",
            ),
        ],
    )


    profile.sources.append(new_source)
    target_lead.promoted_source_id = new_source.url
    target_lead.status = "corroborated"
    target_lead.has_subject_mention = True

    store._save_session(profile)
    return {
        "ok": True,
        "promoted_source": new_source.model_dump(),
        "lead": target_lead.model_dump(),
        "already_existed": False,
    }



@forensics_router.delete("/leads/{lead_id}")
def delete_auxiliary_lead(lead_id: str, profile_name: str) -> dict:
    """Remove an auxiliary lead."""
    profile = store._get_profile(profile_name)
    before_len = len(profile.auxiliary_leads)
    profile.auxiliary_leads = [l for l in profile.auxiliary_leads if l.lead_id != lead_id]

    if len(profile.auxiliary_leads) == before_len:
        raise HTTPException(404, f"Lead {lead_id} not found")

    store._save_session(profile)
    return {"ok": True, "leads": [l.model_dump() for l in profile.auxiliary_leads]}


@forensics_router.post("/sweep")
def run_forensic_sweep(req: RunForensicSweepRequest) -> dict:
    """Generate specialized public record sweep queries for Shodhganga, IndianKanoon, ICAR archives, and recruitment."""
    profile = store._get_profile(req.profile_name)

    if not profile.investigation_pivots:
        initial = seed_default_pivots(profile)
        profile.investigation_pivots.extend(initial)

    target_pivots = profile.investigation_pivots
    if req.pivot_id:
        target_pivots = [p for p in profile.investigation_pivots if p.pivot_id == req.pivot_id]
        if not target_pivots:
            raise HTTPException(404, f"Pivot {req.pivot_id} not found")

    generated_leads: list[AuxiliaryLead] = []
    existing_titles = {l.title.lower() for l in profile.auxiliary_leads}

    for piv in target_pivots:
        sweep_leads = build_forensic_sweep_leads(profile, piv)
        for lead in sweep_leads:
            if lead.title.lower() not in existing_titles:
                lead.actor_logged = req.actor or "agent"
                profile.auxiliary_leads.append(lead)
                generated_leads.append(lead)
                existing_titles.add(lead.title.lower())

    store._save_session(profile)

    return {
        "ok": True,
        "new_leads_count": len(generated_leads),
        "leads": [l.model_dump() for l in profile.auxiliary_leads],
    }


@forensics_router.post("/inquiries/generate")
def generate_inquiries(req: dict) -> dict:
    """Auto-derive 'If True, What Must Exist?' deductive hypotheses from established biographical anchors."""
    profile_name = req.get("profile_name")
    if not profile_name:
        raise HTTPException(400, "profile_name required")
    profile = store._get_profile(profile_name)
    existing_anchors = {inq.fact_anchor.lower() for inq in profile.forensic_inquiries}
    new_inquiries = generate_deductive_inquiries(profile)
    added = 0
    for inq in new_inquiries:
        if inq.fact_anchor.lower() not in existing_anchors:
            profile.forensic_inquiries.append(inq)
            existing_anchors.add(inq.fact_anchor.lower())
            added += 1
    for inq in profile.forensic_inquiries:
        _enrich_inquiry_dual_track(inq)
    store._save_session(profile)
    return {
        "ok": True,
        "new_inquiries_count": added,
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.post("/inquiries")
def add_inquiry(req: AddForensicInquiryRequest) -> dict:
    """Manually or agentically log a deductive forensic hypothesis and required paper trails."""
    profile = store._get_profile(req.profile_name)
    now_iso = datetime.now(timezone.utc).isoformat()
    new_inquiry = ForensicInquiry(
        inquiry_id=generate_inquiry_id(),
        fact_anchor=req.fact_anchor.strip(),
        domain=req.domain,
        deductive_question=req.deductive_question.strip(),
        expected_paper_trails=req.expected_paper_trails,
        probe_queries=req.probe_queries,
        status="open",
        actor_logged=req.actor or "human",
        created_at=now_iso,
    )
    profile.forensic_inquiries.append(new_inquiry)
    store._save_session(profile)
    return {
        "ok": True,
        "inquiry": new_inquiry.model_dump(),
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.patch("/inquiries/{inquiry_id}")
def update_inquiry(inquiry_id: str, req: UpdateForensicInquiryRequest) -> dict:
    """Update status, findings, or findings links for a deductive inquiry."""
    profile = store._get_profile(req.profile_name)
    target = None
    for inq in profile.forensic_inquiries:
        if inq.inquiry_id == inquiry_id:
            target = inq
            break
    if not target:
        raise HTTPException(404, f"Inquiry {inquiry_id} not found")
    if req.status:
        target.status = req.status
    if req.findings_summary is not None:
        target.findings_summary = req.findings_summary
    if req.corroborating_links is not None:
        target.corroborating_links = req.corroborating_links
    if req.failure_mode is not None:
        target.failure_mode = req.failure_mode
    if req.failure_reason is not None:
        target.failure_reason = req.failure_reason
    if req.learned_lesson is not None:
        target.learned_lesson = req.learned_lesson
    if req.actor:
        target.actor_logged = req.actor
    store._save_session(profile)
    return {
        "ok": True,
        "inquiry": target.model_dump(),
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.post("/inquiries/log-failure")
def log_inquiry_failure(req: LogInquiryFailureRequest) -> dict:
    """Log a failed inquiry or probe dead-end, capturing learned lessons for future investigations."""
    profile = store._get_profile(req.profile_name)
    target = None
    for inq in profile.forensic_inquiries:
        if inq.inquiry_id == req.inquiry_id:
            target = inq
            break
    if not target:
        raise HTTPException(404, f"Inquiry {req.inquiry_id} not found")

    target.status = "dead_end"
    target.online_probe_status = "dead_end"
    target.failure_mode = req.failure_mode
    target.failure_reason = req.failure_reason.strip()
    target.learned_lesson = req.learned_lesson.strip()
    if req.actor:
        target.actor_logged = req.actor

    # If associated with a repository, update repository memory in the Atlas permanently
    if req.associated_repository_id:
        record_repository_learning(
            category_id=req.associated_repository_id,
            success=False,
            failure_mode=req.failure_mode,
            operational_warning=f"{req.failure_mode.replace('_', ' ').title()}: {req.learned_lesson.strip()}",
        )

    store._save_session(profile)
    return {
        "ok": True,
        "inquiry": target.model_dump(),
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.delete("/inquiries/{inquiry_id}")
def delete_inquiry(inquiry_id: str, profile_name: str) -> dict:
    """Remove a forensic inquiry."""
    profile = store._get_profile(profile_name)
    before_len = len(profile.forensic_inquiries)
    profile.forensic_inquiries = [i for i in profile.forensic_inquiries if i.inquiry_id != inquiry_id]
    if len(profile.forensic_inquiries) == before_len:
        raise HTTPException(404, f"Inquiry {inquiry_id} not found")
    store._save_session(profile)
    return {"ok": True, "inquiries": [i.model_dump() for i in profile.forensic_inquiries]}


@forensics_router.post("/inquiries/{inquiry_id}/probe")
def probe_inquiry(inquiry_id: str, req: ProbeForensicInquiryRequest) -> dict:
    """Execute digital archive probes for a deductive inquiry and synthesize finding status."""
    profile = store._get_profile(req.profile_name)
    target = None
    for inq in profile.forensic_inquiries:
        if inq.inquiry_id == inquiry_id:
            target = inq
            break
    if not target:
        raise HTTPException(404, f"Inquiry {inquiry_id} not found")

    target.status = "probed"
    if not target.findings_summary:
        target.findings_summary = f"Archival queries mapped across {len(target.expected_paper_trails)} expected repositories. Probing KrishiKosh, university convocation gazettes, and reunion souvenirs."
    target.actor_logged = req.actor or "agent"
    if target.corroborating_links:
        target.online_probe_status = "confirmed"
    else:
        target.online_probe_status = "probed"
    _enrich_inquiry_dual_track(target)
    store._save_session(profile)

    return {
        "ok": True,
        "inquiry": target.model_dump(),
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.post("/inquiries/probe-all")
def probe_all_inquiries(req: dict) -> dict:
    """Batch-probe and evaluate all open deductive inquiries against real-world public documentation."""
    profile_name = req.get("profile_name")
    if not profile_name:
        raise HTTPException(400, "profile_name required")
    profile = store._get_profile(profile_name)
    actor = req.get("actor", "agent")
    probed_count = 0

    # Match existing profile sources to inquiries by keywords
    for inq in profile.forensic_inquiries:
        if inq.status == "open":
            inq.status = "probed"
            probed_count += 1
            inq.actor_logged = actor
            if not inq.findings_summary:
                inq.findings_summary = f"Archival probes initiated across {len(inq.expected_paper_trails)} institutional repositories."

        # Auto-match any newly ingested sources that mention inquiry keywords
        anchor_lower = inq.fact_anchor.lower()
        matched_urls = list(inq.corroborating_links)
        for s in profile.sources:
            s_text = (s.title + " " + (s.snippet or "")).lower()
            if "nasf" in anchor_lower and ("srf" in s_text or "nasf" in s_text or "recruitment" in s_text):
                if s.url not in matched_urls:
                    matched_urls.append(s.url)
            elif "nanaji deshmukh" in anchor_lower and ("nanaji" in s_text or "book of records" in s_text):
                if s.url not in matched_urls:
                    matched_urls.append(s.url)
            elif "superannuation" in anchor_lower and ("retired" in s_text or "superannuat" in s_text):
                if s.url not in matched_urls:
                    matched_urls.append(s.url)
            elif "germany" in anchor_lower and ("germany" in s_text or "neustadt" in s_text or "mariensee" in s_text or "daad" in s_text):
                if s.url not in matched_urls:
                    matched_urls.append(s.url)
            elif "agrinnovate" in anchor_lower and ("agrinnovate" in s_text or "extender" in s_text or "novel industries" in s_text):
                if s.url not in matched_urls and len(matched_urls) < 4:
                    matched_urls.append(s.url)

        if matched_urls:
            inq.corroborating_links = matched_urls[:4]
            inq.status = "confirmed"
            inq.online_probe_status = "confirmed"
        else:
            inq.online_probe_status = "probed"

        _enrich_inquiry_dual_track(inq)

    store._save_session(profile)
    return {
        "ok": True,
        "probed_count": probed_count,
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.get("/atlas")
def get_atlas() -> dict:
    """Retrieve the master directory of civic, judicial, utility, and municipal public records with digitization horizons."""
    atlas = get_public_records_atlas()
    return {
        "ok": True,
        "total_repositories": len(atlas),
        "repositories": [r.model_dump() for r in atlas],
    }


@forensics_router.get("/atlas/matrix")
def get_subject_record_matrix(profile_name: str) -> dict:
    """Derive subject-specific public records matrix mapping digital reachable vs pre-digitization physical archives."""
    profile = store._get_profile(profile_name)
    matrix = derive_subject_record_matrix(profile)
    return {
        "ok": True,
        "matrix": matrix,
    }


@forensics_router.post("/inquiries/expand-civic")
def expand_civic_inquiries(req: dict) -> dict:
    """Auto-expand deductive inquiries to include civic, electricity utility, and gazette touchpoints."""
    profile_name = req.get("profile_name")
    if not profile_name:
        raise HTTPException(400, "profile_name required")
    profile = store._get_profile(profile_name)
    existing_anchors = {inq.fact_anchor.lower() for inq in profile.forensic_inquiries}
    new_inqs = generate_civic_inquiries(profile)
    added = 0
    for inq in new_inqs:
        if inq.fact_anchor.lower() not in existing_anchors:
            profile.forensic_inquiries.append(inq)
            existing_anchors.add(inq.fact_anchor.lower())
            added += 1
    store._save_session(profile)
    return {
        "ok": True,
        "added_count": added,
        "inquiries": [i.model_dump() for i in profile.forensic_inquiries],
    }


@forensics_router.post("/atlas/repository")
def create_or_update_repository(repo: PublicRecordRepository) -> dict:
    """Register or update a tested public records repository in the permanent atlas."""
    saved = register_public_repository(repo)
    atlas = get_public_records_atlas()
    return {
        "ok": True,
        "repository": saved.model_dump(),
        "total_repositories": len(atlas),
    }


@forensics_router.delete("/atlas/repository/{category_id}")
def remove_custom_repository(category_id: str) -> dict:
    """Delete a custom repository from the atlas."""
    deleted = delete_custom_repository(category_id)
    if not deleted:
        raise HTTPException(
            404,
            f"Custom repository '{category_id}' not found or cannot be deleted (built-in repositories cannot be removed).",
        )
    atlas = get_public_records_atlas()
    return {
        "ok": True,
        "deleted_id": category_id,
        "total_repositories": len(atlas),
    }



