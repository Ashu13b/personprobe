#!/usr/bin/env python3
"""Generic, subject-parameterized dry-run harness for PersonProbe.

Exercises the full pipeline on any subject without hardcoded subject literals:
    Stage 1: identify  -> Preview identity candidates, resolve Wikidata QID & enwiki status
    Stage 2: research  -> Start research, summarize sources by reliability & category, report LLM/CSE
    Stage 3: discovery -> Extract pivots, deductive inquiries, atlas repos, OSINT dorks & run residue check
    Stage 4: gate      -> Stop at the human gate (source verification & claim approval are human-only)

After human approval in the UI, resume draft generation with:
    python scripts/dryrun_subject.py --name "<subject>" --resume-draft <session_id>

Usage:
    python scripts/dryrun_subject.py --name "<subject>" [--api http://localhost:3890] [--wikidata <qid>]
    python scripts/dryrun_subject.py --name "<subject>" --resume-draft <session_id>
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Default token blocklist from the de-Yadav specification
DEFAULT_BLOCKLIST = [
    "nimoth",
    "rewari",
    "hisar",
    "cirb",
    "hau",
    "ccshau",
    "buffalo",
    "cloning",
    "gaurav",
    "nasf",
    "sirsa road",
    "125001",
    "125004",
]


def check_differential_residue(
    generated_text: str,
    subject_context_text: str,
    blocklist: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Differential residue check with strict word-boundary matching.

    A blocklist term is a violation ONLY IF:
    1. It appears in the generated discovery output on word boundaries, AND
    2. It does NOT appear in the subject's own input profile, claims, or sources.

    This prevents false positives (e.g. 'cloning' for an actual cloning scientist,
    'gaurav' as a real co-author name, or 'hau' matching Chauhan/Hauz Khas).
    """
    tokens = blocklist if blocklist is not None else DEFAULT_BLOCKLIST
    violations: list[str] = []

    for term in tokens:
        # Match only on whole-word boundaries
        term_pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)

        if term_pattern.search(generated_text):
            # Check if legitimate in subject's own context
            if not term_pattern.search(subject_context_text):
                violations.append(term)

    return len(violations) == 0, violations


def _http_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Perform HTTP JSON request using urllib (no third-party import required)."""
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    encoded_data = None
    if data is not None:
        req_headers["Content-Type"] = "application/json"
        encoded_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url, data=encoded_data, headers=req_headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code} from {url}: {err_body}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"Network error connecting to {url}: {err.reason}") from err


def run_dryrun(
    name: str,
    api_base: str = "http://localhost:3890",
    wikidata_id: str | None = None,
    field: str | None = None,
    affiliation: str | None = None,
    resume_draft_sid: str | None = None,
    blocklist: list[str] | None = None,
) -> int:
    """Run the dryrun harness through its deterministic stages."""
    api_base = api_base.rstrip("/")

    # ──────────────────────────────────────────────────────────────────────────
    # MODE 2: RESUME DRAFT (AFTER HUMAN APPROVAL IN UI)
    # ──────────────────────────────────────────────────────────────────────────
    if resume_draft_sid:
        print(
            f"\n[RESUME DRAFT] Resuming session '{resume_draft_sid}' for subject '{name}'..."
        )
        # 1. Resume session
        resume_res = _http_request(
            f"{api_base}/api/sessions/resume",
            method="POST",
            data={"session_id": resume_draft_sid},
        )
        profile_data = resume_res.get("profile", {})
        profile_name = profile_data.get("name", name)

        # 2. Audit
        audit_res = _http_request(
            f"{api_base}/api/draft/audit/{urllib.parse.quote(profile_name)}",
            method="GET",
        )
        audit_info = audit_res.get("audit", {})
        audit_ready = audit_info.get("ready", False)

        # 3. Generate draft
        draft_res = _http_request(
            f"{api_base}/api/draft",
            method="POST",
            data={"profile_name": profile_name},
        )
        wikitext_en = (
            draft_res.get("wikitext_en")
            or draft_res.get("profile", {}).get("wikitext_en")
            or ""
        )

        # 4. Draft QA
        qa_res = _http_request(
            f"{api_base}/api/draft/qa",
            method="POST",
            data={"profile_name": profile_name},
        )
        qa_passed = qa_res.get("passed", False)
        qa_counts = qa_res.get("counts", {})

        # 5. Differential residue on generated draft
        subject_text = f"{profile_name} {profile_data.get('field', '')} {profile_data.get('affiliation', '')}"
        for claim in profile_data.get("claims", []):
            subject_text += " " + (claim.get("text") or "")

        res_passed, violations = check_differential_residue(
            wikitext_en, subject_text, blocklist=blocklist
        )
        residue_str = "PASS" if res_passed else f"FAIL ({', '.join(violations)})"

        print(
            f"post-approval(audit_ready={audit_ready}, issues={len(audit_info.get('blockers', []))}, "
            f"qa_passed={qa_passed}, qa_counts={qa_counts}, wikitext_chars={len(wikitext_en)}, residue={residue_str})"
        )
        if not res_passed:
            print(
                f"ERROR: Differential Yadav residue detected in final draft: {violations}"
            )
            return 1
        return 0

    # ──────────────────────────────────────────────────────────────────────────
    # MODE 1: INITIAL DISCOVERY & RESEARCH RUN
    # ──────────────────────────────────────────────────────────────────────────

    # Stage 1: identify
    id_payload: dict[str, Any] = {"name": name}
    if field:
        id_payload["field"] = field
    if affiliation:
        id_payload["affiliation"] = affiliation

    id_res = _http_request(f"{api_base}/api/identify", method="POST", data=id_payload)
    candidates = id_res.get("results", []) if isinstance(id_res, dict) else []

    resolved_candidate: dict[str, Any] | None = None
    if wikidata_id:
        for c in candidates:
            if c.get("wikidata_id") == wikidata_id:
                resolved_candidate = c
                break

    if not resolved_candidate and candidates:
        for c in candidates:
            if c.get("kind") == "identity":
                resolved_candidate = c
                break
        if not resolved_candidate:
            resolved_candidate = candidates[0]

    resolved_qid = (
        resolved_candidate.get("wikidata_id") if resolved_candidate else wikidata_id
    )
    has_article = bool(resolved_candidate and resolved_candidate.get("wikipedia_url"))
    cand_count = len(candidates)

    print(
        f"identify(QID={resolved_qid or 'None'}, candidates={cand_count}, article={has_article})"
    )

    # Stage 2: research
    start_payload: dict[str, Any] = {
        "name": name,
        "wikidata_id": resolved_qid,
        "wikipedia_url": resolved_candidate.get("wikipedia_url")
        if resolved_candidate
        else None,
        "field": (resolved_candidate.get("field") if resolved_candidate else None)
        or field,
        "affiliation": (
            resolved_candidate.get("affiliation") if resolved_candidate else None
        )
        or affiliation,
        "nationality": resolved_candidate.get("nationality")
        if resolved_candidate
        else None,
        "birth_year": str(resolved_candidate.get("birth_year") or "") or None
        if resolved_candidate
        else None,
    }

    research_res = _http_request(
        f"{api_base}/api/research/start", method="POST", data=start_payload
    )
    profile_data = research_res.get("profile", {})
    session_id = profile_data.get("session_id", "")
    sources = profile_data.get("sources", [])

    by_reliability = dict(
        collections.Counter(s.get("reliability", "unknown") for s in sources)
    )
    by_category = dict(
        collections.Counter(s.get("source_type", "unknown") for s in sources)
    )

    # Detect LLM provider & Google CSE status
    llm_provider = os.environ.get("PERSONPROBE_LLM")
    if not llm_provider:
        if os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"):
            llm_provider = "Vertex Claude"
        elif os.environ.get("GEMINI_API_KEY"):
            llm_provider = "Gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            llm_provider = "OpenAI"
        else:
            llm_provider = "agent-jobs/stub"

    cse_status = "on" if os.environ.get("GOOGLE_CSE_KEY") else "off"

    print(
        f"research(sources={len(sources)} by_reliability={by_reliability} by_category={by_category}, "
        f"LLM={llm_provider}, CSE={cse_status})"
    )

    # Stage 3: discovery
    encoded_name = urllib.parse.quote(name)
    summary_res = _http_request(
        f"{api_base}/api/forensics/summary?profile_name={encoded_name}", method="GET"
    )
    pivots = summary_res.get("pivots", [])
    inquiries = summary_res.get("inquiries", [])

    civic_res = _http_request(
        f"{api_base}/api/forensics/inquiries/expand-civic",
        method="POST",
        data={"profile_name": name},
    )
    civic_added = civic_res.get("added_count", 0)
    all_inquiries = civic_res.get("inquiries", inquiries)

    matrix_res = _http_request(
        f"{api_base}/api/forensics/atlas/matrix?profile_name={encoded_name}",
        method="GET",
    )
    matrix = matrix_res.get("matrix", {})
    atlas_online = matrix.get("online_reachable", [])
    atlas_offline = matrix.get("offline_archives", [])
    atlas_count = len(atlas_online) + len(atlas_offline)

    dorks_res = _http_request(
        f"{api_base}/api/forensics/dorks?profile_name={encoded_name}", method="GET"
    )
    dorks = dorks_res.get("dorks", [])

    # Collect all generated discovery text
    gen_parts: list[str] = []
    for p in pivots:
        gen_parts.extend(
            [
                p.get("title") or "",
                p.get("description") or "",
                p.get("location") or "",
            ]
        )
    for inq in all_inquiries:
        gen_parts.extend(
            [
                inq.get("fact_anchor") or "",
                inq.get("deductive_question") or "",
                inq.get("offline_archive_location") or "",
                inq.get("offline_custodian") or "",
            ]
        )
        gen_parts.extend([q for q in (inq.get("probe_queries") or []) if q])
        gen_parts.extend([t for t in (inq.get("expected_paper_trails") or []) if t])
    for r in atlas_online + atlas_offline:
        gen_parts.extend(
            [
                r.get("category_name") or "",
                r.get("offline_repository_name") or "",
                r.get("offline_custodian") or "",
                r.get("custom_search_query") or "",
            ]
        )
    for d in dorks:
        gen_parts.extend(
            [
                d.get("title") or "",
                d.get("query") or "",
                d.get("description") or "",
            ]
        )

    generated_text = " ".join(str(p) for p in gen_parts if p)

    # Subject's own input text (legitimate context)
    sub_parts: list[str] = [
        name,
        profile_data.get("field", "") or "",
        profile_data.get("affiliation", "") or "",
        profile_data.get("known_for", "") or "",
    ]
    for cl in profile_data.get("claims", []):
        sub_parts.append(cl.get("text", "") or "")
    for s in sources:
        sub_parts.extend(
            [
                s.get("title", "") or "",
                s.get("url", "") or "",
                s.get("snippet", "") or "",
            ]
        )

    subject_context_text = " ".join(sub_parts)

    res_passed, violations = check_differential_residue(
        generated_text, subject_context_text, blocklist=blocklist
    )
    residue_str = "PASS" if res_passed else f"FAIL ({', '.join(violations)})"

    print(
        f"discovery(pivots={len(pivots)}, inquiries={len(all_inquiries)}, "
        f"dorks={len(dorks)}, atlas={atlas_count}, civic={civic_added}, residue={residue_str})"
    )

    if not res_passed:
        print(f"ERROR: Differential residue check failed! Leaking terms: {violations}")
        return 1

    # Stage 4: Human Gate (HARD RULE 1: Never automate source verify or claim approve)
    print(
        f"\n[GATE] Session ID: {session_id} — Awaiting human verify/approve in UI.\n"
        f"Source verification and claim approval are reserved for the human editor.\n"
        f"To resume draft generation after human review in the UI, run:\n"
        f'    python scripts/dryrun_subject.py --name "{name}" --resume-draft {session_id}\n'
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic, subject-parameterized dry-run harness for PersonProbe."
    )
    parser.add_argument("--name", required=True, help="Subject full name")
    parser.add_argument(
        "--api",
        default="http://localhost:3890",
        help="Base URL of running PersonProbe server (default: http://localhost:3890)",
    )
    parser.add_argument(
        "--wikidata", default=None, help="Wikidata QID hint (e.g. Q131160362)"
    )
    parser.add_argument(
        "--field", default=None, help="Subject academic/professional field"
    )
    parser.add_argument(
        "--affiliation", default=None, help="Subject institutional affiliation"
    )
    parser.add_argument(
        "--resume-draft",
        default=None,
        help="Session ID to resume post-approval for draft generation and QA auditing",
    )

    args = parser.parse_args()

    sys.exit(
        run_dryrun(
            name=args.name,
            api_base=args.api,
            wikidata_id=args.wikidata,
            field=args.field,
            affiliation=args.affiliation,
            resume_draft_sid=args.resume_draft,
        )
    )


if __name__ == "__main__":
    main()
