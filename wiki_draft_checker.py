#!/usr/bin/env python3
"""Standalone Wiki Draft Checker Engine.

Deterministic Verification & Intelligence Layer for Wikipedia Articles & AfC Drafts.
Works independently on ANY wikitext draft from any process, human, or repository.

Verifies:
  1. Link & Citation Integrity: Empty links, dead links, malformed URLs, dirty titles.
  2. Sentence-to-Link Matching: Link & text alignment, ungrounded claims, empty refs.
  3. WP:BLP & Privacy: Residential addresses, phone numbers, private personal data.
  4. WP:NPOV & Tone: Puffery, peacock terms, promotional phrasing.
  5. WP:MOS Structure: Infobox, short description, lead quality, reflist, categories.

Usage:
  CLI:
    python3 wiki_draft_checker.py <file_or_text> [--json] [--no-live-links]
  Python:
    from wiki_draft_checker import check_wiki_draft, DraftCheckerReport
    report = check_wiki_draft(wikitext, check_live_links=True)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import concurrent.futures
from dataclasses import dataclass, field, asdict


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------


@dataclass
class CheckFinding:
    category: str  # "links" | "grounding" | "blp_privacy" | "npov_tone" | "structure"
    severity: str  # "CRITICAL" | "ERROR" | "WARNING" | "INFO"
    rule_id: str  # e.g. "empty_url", "link_text_mismatch", "peacock_term"
    message: str  # Human-readable explanation
    context: str = ""  # The problematic snippet or sentence
    line_num: int = 0  # Approximate line number if detectable
    suggestion: str = ""  # Actionable guidance


@dataclass
class LinkAuditResult:
    url: str
    ref_name: str = ""
    status: str = (
        "valid"  # "valid" | "empty" | "malformed" | "dead" | "redirect" | "unverified"
    )
    status_code: int | None = None
    title: str = ""
    domain: str = ""
    is_archived: bool = False
    error_message: str = ""


@dataclass
class SentenceGroundingResult:
    sentence: str
    has_citation: bool
    citation_count: int
    matched_links: list[str] = field(default_factory=list)
    relevance_score: float = 1.0  # 0.0 to 1.0 estimate of link-text alignment
    flag: str = "ok"  # "ok" | "ungrounded" | "mismatch_suspected"


@dataclass
class DraftCheckerReport:
    verdict: str  # "PASS" | "WARN" | "FAIL"
    quality_score: int  # 0 to 100
    sentence_count: int
    total_citations: int
    unique_links_count: int
    findings: list[CheckFinding] = field(default_factory=list)
    link_audits: list[LinkAuditResult] = field(default_factory=list)
    grounding: list[SentenceGroundingResult] = field(default_factory=list)
    counts_by_severity: dict[str, int] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Rules & Regex Patterns
# -----------------------------------------------------------------------------

PEACOCK_TERMS = [
    r"\bworld[- ]renowned\b",
    r"\bvisionary\b",
    r"\blegendary\b",
    r"\bpioneering\b",
    r"\brevolutionary\b",
    r"\bgenius\b",
    r"\bunparalleled\b",
    r"\bextraordinary\b",
    r"\binnovative masterpiece\b",
    r"\bprestigious\b",
    r"\bfamous\b",
    r"\bremarkable\b",
    r"\bacclaimed\b",
    r"\bcelebrated\b",
    r"\bunprecedented\b",
]

PRIVACY_PATTERNS = [
    (
        r"\b(?:house|flat|plot|h\.?\s*no\.?)\s*[:#-]?\s*\d+[a-z]?",
        "Specific residential plot/house number (WP:BLP)",
    ),
    (
        r"\b(?:sector|pocket|ward)\s*[-#]?\s*\d+[a-z]?",
        "Granular urban sector or municipal ward footprint (WP:BLP)",
    ),
    (
        r"(?<!isbn\s)(?<!isbn:\s)(?<!isbn-10:\s)(?<!isbn-13:\s)(?<!\d)\b(?:\+?91[\s-]?)?[6-9]\d{9}\b(?!\d)",
        "Indian mobile or personal phone number (WP:BLP)",
    ),
    (r"\b0\d{2,4}[-\s]?\d{6,8}\b", "Landline phone number with STD area code (WP:BLP)"),
    (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "Personal/work email address (WP:BLP)",
    ),
    (
        r"\b(?:son|daughter|child|wife|husband|spouse)\s+(?:of|is|named)\s+[A-Z][a-z]+",
        "Private immediate non-notable family name (WP:BLP)",
    ),
]

DIRTY_TITLE_PATTERNS = [
    (r"\.\.\.$|…$", "Title ends in ellipsis / truncation"),
    (r"\s\|\s", "Title contains unescaped pipe separator '|'"),
    (r"^https?://", "Title is a bare raw URL instead of an article headline"),
    (
        r"^(?:home|index|welcome|page not found|access denied|403 forbidden|404)$",
        "Title is placeholder or error text",
    ),
]

ISO_DATE_PATTERN = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Sentence splitting abbreviation protection
ABBREVIATIONS = [
    "dr.",
    "prof.",
    "mr.",
    "mrs.",
    "ms.",
    "sh.",
    "smt.",
    "p.s.",
    "p. s.",
    "al.",
    "etc.",
    "eds.",
    "ed.",
    "b.sc.",
    "m.sc.",
    "ph.d.",
    "i.e.",
    "e.g.",
    "vol.",
    "no.",
    "pp.",
    "jan.",
    "feb.",
    "mar.",
    "apr.",
    "jun.",
    "jul.",
    "aug.",
    "sep.",
    "sept.",
    "oct.",
    "nov.",
    "dec.",
]


# -----------------------------------------------------------------------------
# Core Checker Implementation
# -----------------------------------------------------------------------------


class WikiDraftChecker:
    """Deterministic and Intelligent Wiki Draft Checker."""

    def __init__(self, check_live_links: bool = True, timeout: int = 5):
        self.check_live_links = check_live_links
        self.timeout = timeout

    def check(self, wikitext: str) -> DraftCheckerReport:
        findings: list[CheckFinding] = []
        clean_text = wikitext.strip()

        if not clean_text:
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="CRITICAL",
                    rule_id="empty_draft",
                    message="Draft wikitext is completely empty.",
                    suggestion="Provide wikitext content to check.",
                )
            )
            return DraftCheckerReport(
                verdict="FAIL",
                quality_score=0,
                sentence_count=0,
                total_citations=0,
                unique_links_count=0,
                findings=findings,
                counts_by_severity={"CRITICAL": 1, "ERROR": 0, "WARNING": 0, "INFO": 0},
            )

        # 1. Structural Audits
        self._check_structure(clean_text, findings)

        # 2. Extract and Audit Citations & Links
        link_audits = self._check_links_and_citations(clean_text, findings)

        # 3. Grounding & Sentence-to-Link Alignment
        grounding_results = self._check_sentence_grounding(
            clean_text, link_audits, findings
        )

        # 4. BLP & Privacy Scans
        self._check_privacy_and_blp(clean_text, findings)

        # 5. Tone & Neutrality Scans
        self._check_tone_and_npov(clean_text, findings)

        # 6. Compute Counts & Verdict Score
        counts: dict[str, int] = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        # Scoring algorithm
        score = 100
        score -= counts["CRITICAL"] * 40
        score -= counts["ERROR"] * 15
        score -= counts["WARNING"] * 4
        score -= counts["INFO"] * 1
        score = max(0, min(100, score))

        if counts["CRITICAL"] > 0 or counts["ERROR"] >= 2 or score < 50:
            verdict = "FAIL"
        elif counts["ERROR"] > 0 or counts["WARNING"] >= 3 or score < 80:
            verdict = "WARN"
        else:
            verdict = "PASS"

        return DraftCheckerReport(
            verdict=verdict,
            quality_score=score,
            sentence_count=len(grounding_results),
            total_citations=len(re.findall(r"<ref[ >]", clean_text, re.I)),
            unique_links_count=len(link_audits),
            findings=findings,
            link_audits=link_audits,
            grounding=grounding_results,
            counts_by_severity=counts,
        )

    # -------------------------------------------------------------------------
    # Structural Audits
    # -------------------------------------------------------------------------

    def _check_structure(self, wikitext: str, findings: list[CheckFinding]) -> None:
        if "{{short description" not in wikitext.lower():
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="ERROR",
                    rule_id="missing_short_description",
                    message="Missing {{Short description|...}} template at the top of the article.",
                    suggestion="Add {{Short description|...}} to summarize the subject's primary role in under 40 characters.",
                )
            )

        if not re.search(r"\{\{Infobox\s+\w+", wikitext, re.I):
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="ERROR",
                    rule_id="missing_infobox",
                    message="Missing {{Infobox ...}} template. Wikipedia AfC expects standard structured biographical infoboxes.",
                    suggestion="Add an appropriate infobox, such as {{Infobox scientist}} or {{Infobox person}}.",
                )
            )

        if not re.search(r"\{\{reflist\b|<references\s*/>", wikitext, re.I):
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="CRITICAL",
                    rule_id="missing_reflist",
                    message="Missing {{reflist}} or <references/> tag. Citations will fail to display to readers.",
                    suggestion="Place '== References ==\\n{{reflist}}' near the bottom of the article.",
                )
            )

        # Check lead paragraph
        lead_match = re.split(r"^==[^=]", wikitext, maxsplit=1, flags=re.M)
        lead = lead_match[0] if lead_match else wikitext
        # Remove templates and comments
        lead_prose = re.sub(r"\{\{.*?\}\}", "", lead, flags=re.S)
        lead_prose = re.sub(r"<!--.*?-->", "", lead_prose, flags=re.S)
        lead_prose = re.sub(r"<ref[^>]*>.*?</ref>", "", lead_prose, flags=re.S)
        lead_prose = re.sub(r"<ref[^>]*/>", "", lead_prose)
        lead_sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", lead_prose)
            if len(s.strip()) > 15
        ]

        if len(lead_sentences) < 2:
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="WARNING",
                    rule_id="thin_lead",
                    message=f"Lead section contains only {len(lead_sentences)} substantive sentence(s). AfC reviewers expect 2–4 comprehensive sentences.",
                    suggestion="Expand the lead to summarize the subject's notable career, breakthroughs, and primary significance.",
                )
            )

        if "[[category:" not in wikitext.lower():
            findings.append(
                CheckFinding(
                    category="structure",
                    severity="WARNING",
                    rule_id="missing_categories",
                    message="No [[Category:...]] tags found.",
                    suggestion="Add relevant categories (e.g., [[Category:YYYY births]], [[Category:Living people]], and discipline categories).",
                )
            )

    # -------------------------------------------------------------------------
    # Link & Citation Forensics
    # -------------------------------------------------------------------------

    def _check_links_and_citations(
        self, wikitext: str, findings: list[CheckFinding]
    ) -> list[LinkAuditResult]:
        audits: list[LinkAuditResult] = []
        seen_urls: set[str] = set()

        # 1. Bare external link check
        for m in re.finditer(r"\[(https?://[^\s\]]+)(?:\s+([^\]]*))?\]", wikitext):
            url = m.group(1).strip()
            pos = m.start()
            is_in_ref = bool(re.search(r"<ref[^>]*>[^<]*$", wikitext[:pos], re.I))
            if not is_in_ref:
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="ERROR",
                        rule_id="bare_external_link_in_prose",
                        message=f"Bare external link in article body: [{url}] — Wikipedia MOS forbids external links in prose.",
                        context=m.group(0),
                        suggestion="Move this link into an inline <ref>{{cite web|...}}</ref> footnote.",
                    )
                )

        # 2. Extract cite templates inside <ref>
        ref_matches = list(
            re.finditer(
                r"<ref(?:\s+name=[\"']?([^\"'>\s]+)[\"']?)?\s*>(.*?)</ref>",
                wikitext,
                re.S | re.I,
            )
        )

        # Check for empty ref tags
        for m in re.finditer(r"<ref\s*>\s*</ref>", wikitext, re.I):
            findings.append(
                CheckFinding(
                    category="links",
                    severity="CRITICAL",
                    rule_id="empty_ref_tag",
                    message="Found empty <ref></ref> container with zero content or citation.",
                    context="<ref></ref>",
                    suggestion="Remove empty ref tag or populate it with a valid citation.",
                )
            )

        for rm in ref_matches:
            ref_name = rm.group(1) or ""
            ref_body = rm.group(2).strip()

            if not ref_body:
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="CRITICAL",
                        rule_id="empty_ref_body",
                        message=f"Reference '{ref_name}' has an empty body.",
                        context=rm.group(0),
                        suggestion="Provide a valid citation or URL inside the reference.",
                    )
                )
                continue

            # Check for URL parameter
            url_match = re.search(r"\burl\s*=\s*([^|}\s]+)", ref_body, re.I)
            url = url_match.group(1).strip() if url_match else ""

            # Check for empty URL in citation template
            if re.search(
                r"\{\{cite\s+web[^}]*\burl\s*=\s*(?:[|}\s]|$)", ref_body, re.I
            ):
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="CRITICAL",
                        rule_id="empty_citation_url",
                        message=f"Citation template has an empty 'url=' parameter in ref '{ref_name}'.",
                        context=ref_body[:100],
                        suggestion="Provide the direct URL to the source.",
                    )
                )

            if not url:
                # Could be a book/journal cite without URL
                if (
                    "cite book" in ref_body.lower()
                    or "cite journal" in ref_body.lower()
                    or "isbn" in ref_body.lower()
                ):
                    continue
                if "cite web" in ref_body.lower():
                    findings.append(
                        CheckFinding(
                            category="links",
                            severity="ERROR",
                            rule_id="cite_web_missing_url",
                            message="Template {{cite web}} requires a valid 'url=' parameter.",
                            context=ref_body[:100],
                        )
                    )
                continue

            # Validate URL Scheme
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="CRITICAL",
                        rule_id="malformed_url_scheme",
                        message=f"Malformed URL '{url}': Missing 'http://' or 'https://' protocol.",
                        context=url,
                        suggestion="Ensure all citations have absolute, valid protocols.",
                    )
                )
                audits.append(
                    LinkAuditResult(
                        url=url,
                        ref_name=ref_name,
                        status="malformed",
                        error_message="Missing protocol",
                    )
                )
                continue

            # Cleanliness of Title
            title_match = re.search(r"\btitle\s*=\s*([^|}\n]+)", ref_body, re.I)
            title = title_match.group(1).strip() if title_match else ""
            if not title:
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="WARNING",
                        rule_id="missing_citation_title",
                        message=f"Citation for '{url}' has no 'title=' specified.",
                        context=ref_body[:100],
                    )
                )
            else:
                for dirty_re, desc in DIRTY_TITLE_PATTERNS:
                    if re.search(dirty_re, title, re.I):
                        findings.append(
                            CheckFinding(
                                category="links",
                                severity="ERROR",
                                rule_id="dirty_citation_title",
                                message=f"Invalid citation title '{title}': {desc}.",
                                context=title,
                                suggestion="Provide a clean, un-truncated article title without pipes or raw URLs.",
                            )
                        )

            # Date format check
            date_match = re.search(r"\bdate\s*=\s*([^|}\n]+)", ref_body, re.I)
            if date_match:
                raw_date = date_match.group(1).strip()
                if ISO_DATE_PATTERN.search(raw_date):
                    findings.append(
                        CheckFinding(
                            category="links",
                            severity="WARNING",
                            rule_id="iso_date_format",
                            message=f"Citation date '{raw_date}' is formatted as ISO (YYYY-MM-DD). Wikipedia AfC prefers standard DMY/MDY format (e.g. '10 April 2024').",
                            context=raw_date,
                            suggestion=f"Convert '{raw_date}' to standard date format.",
                        )
                    )

            if url in seen_urls:
                continue
            seen_urls.add(url)

            audits.append(
                LinkAuditResult(
                    url=url,
                    ref_name=ref_name,
                    title=title,
                    domain=parsed.netloc,
                    is_archived="archive.org" in parsed.netloc
                    or "archive.today" in parsed.netloc
                    or "archive.ph" in parsed.netloc,
                )
            )

        # Check live link reachability if requested
        if self.check_live_links and audits:
            self._verify_live_links(audits, findings)

        return audits

    def _verify_live_links(
        self, audits: list[LinkAuditResult], findings: list[CheckFinding]
    ) -> None:
        """Concurrent HTTP verification of all external citations."""

        def probe(audit: LinkAuditResult) -> None:
            if audit.status == "malformed":
                return
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            req = urllib.request.Request(audit.url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    audit.status_code = resp.status
                    if resp.status in (200, 201, 206, 301, 302):
                        audit.status = "valid"
                    else:
                        audit.status = "unexpected_status"
            except urllib.error.HTTPError as e:
                audit.status_code = e.code
                if e.code == 404:
                    audit.status = "dead"
                    audit.error_message = "HTTP 404 Not Found"
                elif e.code == 403:
                    audit.status = "restricted"
                    audit.error_message = "HTTP 403 Forbidden / Cloudflare Protection"
                elif e.code >= 500:
                    audit.status = "server_error"
                    audit.error_message = f"HTTP {e.code} Server Error"
                else:
                    audit.status = "http_error"
                    audit.error_message = f"HTTP {e.code}"
            except Exception as e:
                audit.status = "connection_failed"
                audit.error_message = str(e)[:60]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(probe, audits)

        for audit in audits:
            if audit.status == "dead":
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="CRITICAL",
                        rule_id="dead_citation_url",
                        message=f"Dead citation URL: '{audit.url}' returned HTTP 404 Not Found.",
                        context=audit.url,
                        suggestion="Replace with an active source URL or attach an archive URL.",
                    )
                )
            elif audit.status == "server_error":
                findings.append(
                    CheckFinding(
                        category="links",
                        severity="ERROR",
                        rule_id="server_error_url",
                        message=f"Source server error: '{audit.url}' returned {audit.error_message}.",
                        context=audit.url,
                        suggestion="Verify server availability or replace with an archived mirror.",
                    )
                )

    # -------------------------------------------------------------------------
    # Sentence-to-Link Grounding & Text Matching
    # -------------------------------------------------------------------------

    def _split_into_sentences(self, text: str) -> list[str]:
        """Intelligent sentence boundary detector protecting common abbreviations."""
        # Replace abbreviation periods with placeholder
        placeholder_text = text
        for abbr in ABBREVIATIONS:
            # Case insensitive replace
            pattern = re.compile(re.escape(abbr), re.I)
            placeholder_text = pattern.sub(abbr.replace(".", "§DOT§"), placeholder_text)

        # Protect initial patterns like 'P. S.' or 'A. B.'
        placeholder_text = re.sub(
            r"\b([A-Z])\.\s*([A-Z])\.", r"\1§DOT§ \2§DOT§", placeholder_text
        )
        placeholder_text = re.sub(r"\b([A-Z])\.", r"\1§DOT§", placeholder_text)

        # Split on sentence boundaries
        raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'\[])", placeholder_text)

        sentences = []
        for s in raw_splits:
            restored = s.replace("§DOT§", ".").strip()
            if restored:
                sentences.append(restored)
        return sentences

    def _check_sentence_grounding(
        self,
        wikitext: str,
        link_audits: list[LinkAuditResult],
        findings: list[CheckFinding],
    ) -> list[SentenceGroundingResult]:
        results: list[SentenceGroundingResult] = []
        audit_by_url = {a.url: a for a in link_audits}

        # Filter out bibliography, external links, and footer lines (starting with *, ;, ==)
        body_lines = []
        in_references_or_notes = False

        for line in wikitext.splitlines():
            s = line.strip()
            if not s or s.startswith(("{", "|", "!", "}")):
                continue
            if s.startswith("=="):
                header = s.lower()
                if any(
                    k in header
                    for k in [
                        "references",
                        "see also",
                        "further reading",
                        "external links",
                        "selected publications",
                    ]
                ):
                    in_references_or_notes = True
                else:
                    in_references_or_notes = False
                continue
            if in_references_or_notes or s.startswith(("*", ";", "#")):
                continue
            body_lines.append(s)

        prose = " ".join(body_lines)
        sentences = self._split_into_sentences(prose)

        for s_clean in sentences:
            if len(s_clean) < 25:
                continue

            # Extract attached refs
            refs_in_s = list(
                re.finditer(
                    r"<ref(?:\s+name=[\"']?([^\"'>\s]+)[\"']?)?(?:\s*/>|>(.*?)</ref>)",
                    s_clean,
                    re.S | re.I,
                )
            )
            matched_links: list[str] = []

            for rm in refs_in_s:
                ref_text = rm.group(0)
                url_m = re.search(r"url=([^|}\s]+)", ref_text, re.I)
                if url_m:
                    matched_links.append(url_m.group(1).strip())
                elif rm.group(1):
                    # Named ref lookup
                    ref_name = rm.group(1)
                    for la in link_audits:
                        if la.ref_name == ref_name:
                            matched_links.append(la.url)
                            break

            # Strip markup to analyze sentence semantic tokens
            pure_sentence = re.sub(r"<ref[^>]*>.*?</ref>", "", s_clean, flags=re.S)
            pure_sentence = re.sub(r"<ref[^>]*/>", "", pure_sentence)
            pure_sentence = re.sub(
                r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", pure_sentence
            )
            pure_sentence = re.sub(r"'''?", "", pure_sentence).strip()

            if not refs_in_s and len(pure_sentence) > 35:
                findings.append(
                    CheckFinding(
                        category="grounding",
                        severity="ERROR",
                        rule_id="ungrounded_sentence",
                        message="Sentence asserts factual claims with no inline citation.",
                        context=pure_sentence[:120],
                        suggestion="Attach an inline <ref> citation supporting these facts.",
                    )
                )
                results.append(
                    SentenceGroundingResult(
                        sentence=pure_sentence,
                        has_citation=False,
                        citation_count=0,
                        flag="ungrounded",
                        relevance_score=0.0,
                    )
                )
                continue

            # Semantic Link-Text Match: Compare words
            sentence_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", pure_sentence.lower()))
            relevance = 1.0

            if matched_links:
                combined_citation_text = ""
                for u in matched_links:
                    la = audit_by_url.get(u)
                    if la:
                        combined_citation_text += f" {la.title} {la.domain}"
                    # Also include semantic tokens from URL path
                    path_tokens = " ".join(re.findall(r"[a-zA-Z]{3,}", u))
                    combined_citation_text += f" {path_tokens}"

                # Check for Devanagari or English words
                citation_words = set(
                    re.findall(r"\b[a-zA-Z]{4,}\b", combined_citation_text.lower())
                )
                common_tokens = sentence_words.intersection(citation_words)
                has_devanagari = bool(
                    re.search(r"[\u0900-\u097F]", combined_citation_text)
                )

                # Only flag suspected mismatch if both are English and zero overlap
                if (
                    not has_devanagari
                    and len(sentence_words) >= 6
                    and len(common_tokens) == 0
                ):
                    relevance = 0.5
                    findings.append(
                        CheckFinding(
                            category="grounding",
                            severity="INFO",
                            rule_id="link_text_mismatch_advisory",
                            message="Informational: Zero direct lexical overlap between sentence tokens and citation title/URL path.",
                            context=f"Sentence: '{pure_sentence[:80]}...' vs Citation: '{combined_citation_text.strip()[:60]}...'",
                            suggestion="Verify that the linked source directly discusses the specific facts in this sentence.",
                        )
                    )

            results.append(
                SentenceGroundingResult(
                    sentence=pure_sentence,
                    has_citation=bool(refs_in_s),
                    citation_count=len(refs_in_s),
                    matched_links=matched_links,
                    relevance_score=relevance,
                    flag="mismatch_suspected" if relevance < 0.5 else "ok",
                )
            )

        return results

    # -------------------------------------------------------------------------
    # BLP & Privacy Scans
    # -------------------------------------------------------------------------

    def _check_privacy_and_blp(
        self, wikitext: str, findings: list[CheckFinding]
    ) -> None:
        # Strip bibliographic identifiers (ISBN, ISSN, DOI, PMID, PMC) and URLs before scanning for phone numbers
        sanitized = re.sub(r"https?://[^\s|\]}\"']+", " ", wikitext)
        sanitized = re.sub(
            r"\|\s*(?:isbn(?:-10|-13)?|issn|pmid|pmc|doi|bibcode|oclc)\s*=\s*[^|}\n]+",
            " ",
            sanitized,
            flags=re.I,
        )
        sanitized = re.sub(
            r"\bISBN(?:-10|-13)?\s*[:=-]?\s*[\d\-X]+", " ", sanitized, flags=re.I
        )

        for pat, desc in PRIVACY_PATTERNS:
            for m in re.finditer(pat, sanitized, re.I):
                findings.append(
                    CheckFinding(
                        category="blp_privacy",
                        severity="CRITICAL",
                        rule_id="blp_privacy_violation",
                        message=f"Privacy violation ({desc}): Found '{m.group(0)}'. Wikipedia WP:BLP strictly forbids publishing private addresses, phones, or non-notable family details.",
                        context=m.group(0),
                        suggestion="Remove private identifier from public draft text. Keep only in offline research dossier.",
                    )
                )

    # -------------------------------------------------------------------------
    # Tone & Neutrality Scans
    # -------------------------------------------------------------------------

    def _check_tone_and_npov(self, wikitext: str, findings: list[CheckFinding]) -> None:
        unquoted = re.sub(r"\"[^\"]*\"", "", wikitext)
        unquoted = re.sub(r"“[^”]*”", "", unquoted)
        unquoted = re.sub(r"<ref[^>]*>.*?</ref>", "", unquoted, flags=re.S)

        for p_term in PEACOCK_TERMS:
            for m in re.finditer(p_term, unquoted, re.I):
                findings.append(
                    CheckFinding(
                        category="npov_tone",
                        severity="WARNING",
                        rule_id="peacock_term",
                        message=f"Promotional/peacock term detected: '{m.group(0)}'. Violates WP:NPOV neutral tone.",
                        context=m.group(0),
                        suggestion="Restate factually using objective evidence rather than subjective adjectives.",
                    )
                )


# -----------------------------------------------------------------------------
# Public API & Standalone Runner
# -----------------------------------------------------------------------------


def check_wiki_draft(
    wikitext: str, check_live_links: bool = True, timeout: int = 5
) -> DraftCheckerReport:
    """Entry point for checking any arbitrary wikitext draft."""
    checker = WikiDraftChecker(check_live_links=check_live_links, timeout=timeout)
    return checker.check(wikitext)


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Wiki Draft & AfC Checker")
    parser.add_argument(
        "input", help="File path containing wikitext, or raw wikitext string"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output report as formatted JSON"
    )
    parser.add_argument(
        "--no-live-links",
        action="store_true",
        help="Skip live HTTP checking of external links",
    )
    parser.add_argument(
        "--timeout", type=int, default=5, help="HTTP timeout in seconds"
    )

    args = parser.parse_args()

    # Read from file if exists, else treat input as raw string
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        content = args.input

    checker = WikiDraftChecker(
        check_live_links=not args.no_live_links, timeout=args.timeout
    )
    report = checker.check(content)

    if args.json:
        print(json.dumps(asdict(report), indent=2))
        sys.exit(0 if report.verdict != "FAIL" else 1)

    # Human-friendly Terminal Output
    print("=" * 70)
    print("         STANDALONE WIKIPEDIA DRAFT INTEGRITY AUDIT REPORT         ")
    print("=" * 70)
    status_icon = (
        "✅"
        if report.verdict == "PASS"
        else ("⚠️" if report.verdict == "WARN" else "❌")
    )
    print(f"VERDICT:       {status_icon} {report.verdict}")
    print(f"QUALITY SCORE: {report.quality_score}/100")
    print(
        f"METRICS:       {report.sentence_count} prose sentences · {report.total_citations} citations · {report.unique_links_count} unique URLs"
    )
    print(
        f"FINDINGS:      {report.counts_by_severity.get('CRITICAL', 0)} Critical · {report.counts_by_severity.get('ERROR', 0)} Errors · {report.counts_by_severity.get('WARNING', 0)} Warnings"
    )
    print("-" * 70)

    if report.findings:
        print("ISSUES FOUND:")
        for idx, f in enumerate(report.findings, 1):
            sev_badge = f"[{f.severity}]"
            print(
                f"  {idx:2d}. {sev_badge:10s} ({f.category}) {f.rule_id}: {f.message}"
            )
            if f.context:
                print(f'      Context:    "{f.context.strip()}"')
            if f.suggestion:
                print(f"      Resolution: {f.suggestion}")
        print("-" * 70)
    else:
        print(
            "✨ No errors or policy violations detected! Draft is clean and AfC-ready."
        )
        print("-" * 70)

    print(f"LINK AUDIT ({len(report.link_audits)} links):")
    for la in report.link_audits[:15]:
        status_ico = (
            "🟢"
            if la.status == "valid"
            else ("🔴" if la.status in ("dead", "malformed") else "🟡")
        )
        code_str = f"[{la.status_code}]" if la.status_code else ""
        print(
            f"  {status_ico} {la.status:10s} {code_str:6s} {la.domain[:25]:25s} | {la.title[:35]}"
        )
    if len(report.link_audits) > 15:
        print(f"  ... and {len(report.link_audits) - 15} more links.")
    print("=" * 70)

    sys.exit(0 if report.verdict != "FAIL" else 1)


if __name__ == "__main__":
    main()
