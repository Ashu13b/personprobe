# Research Audit — Dr. Prem Singh Yadav (ICAR-CIRB)
**Auditor role:** independent research audit of the PersonProbe session `py-prem-singh-yadav-569e5aea`
**Date:** 21 September 2026 · **Subject:** Indian animal-reproduction scientist, buffalo cloning; retired 30 Apr 2025

---

## 1. Scope & method
- **Transports:** clean scholarly APIs (OpenAlex, Crossref, PubMed/NCBI, Semantic Scholar), institutional PDF corpus,
  and the OpenScrape mobile-bridge (carrier IP) for bot-walled press/registries. VM HTTP used for open hosts only.
- **Corpus:** 476 active sources on **109 domains** — 277 authored publications, 92 independent secondary,
  59 institutional, 38 general web, 8 self-published, 1 record registry, 1 CV blueprint; **140** discarded
  (namesakes, retail mirrors, unverifiable) kept in a recoverable registry.
- **Honesty controls:** session-scoped namesake registry (2 signatures), identity-strength gate
  (initials-only matches attach as *suspect*), CV-as-input rule (never citable), link-identity dedup only.

## 2. Evidence base — volume
| Measure | Value |
|---|---|
| Active sources / domains | 476 / 109 |
| Name-bearing sources | ~250 |
| Multi-link facts (clusters) | 34 of 185 facts |
| Independent secondary coverage origins assessed significant | 16 |
| Notability engine verdict | **"Strong coverage"** — 15 significant origins, 39 candidates |
| Registry metrics (Vidwan 249594) | 85 publications · 976 Scopus cites (h=19) · 761 Crossref cites (h=17) |

## 3. Identity & namesake discipline — strong
- Career-long homonym risk was real and handled: **39 "other-Yadav" DOI records rejected** and kept in the
  discard registry; **2 Vidwan neighbours** flagged wrong-person; the identity bond uses the **Scopus ID
  57225411188** (OpenAlex A5111039070 ↔ Vidwan 249594) rather than name spelling.
- Co-author network (113 authors, incl. FLI Germany and Univ. of Missouri) built from the bonded author id, not
  name search — the strongest available guard against conflation.

## 4. Claim integrity — the weakest layer (findings)
| Finding | Severity | Evidence |
|---|---|---|
| **Verbatim quote coverage is low** — only **12 of 284** claims carry `settled_quote` (L4 evidence) | High | API counts |
| **Actor attribution incomplete** — 261 claims confirmed, but only **33** carry a verifier trail; 0 human-verified | High | `verified_by` distribution (legacy claims predate the L4 trail) |
| **`human_verified` flag is over-set** — 407 sources marked, versus 4 identity-confirmed and 16 assessed-significant | High | flag vs state cross-tab |
| **Coverage depth mostly unassessed** — 433/476 `unassessed` (only 16 significant) | Medium | source field distribution |
| 9 facts blocked, 5 need source verification | Low (working as designed) | draft-suggestions |
- Consequence: draft approvals robust *on source strength*, but **not yet quote-auditable line by line**; an
  independent reviewer cannot re-derive 272 confirmed facts from stored quotes today.

## 5. Key life-facts corroboration matrix
| Fact | Independent evidence | Institutional | Authored | Link depth |
|---|---|---|---|---|
| Born 10 Apr 1963, Nimoth, Rewari | Amar Ujala (retirement) | CIRB staff-list PDF | CV (non-citable) | 2 links |
| Education: HAU Hisar B.Sc 1985 / M.Sc 1987 / Ph.D 1991 | — | publisher bio, staff records | CV | thin (1–2) |
| ICAR service from 12 Apr 1993 | press features | ICAR circulars, annual reports | CV | 2–3 |
| PI, buffalo cloning programme (2010–2022+) | Tribune/TOI/Zee/India.com (4–10 links) | ICAR releases, ARs | papers/chapters | **strong** |
| Hisar Gaurav (2015), M-29 ×7 + re-clone (2020) | multiple dailies; Bhaskar/Jagran/Amar Ujala | ICAR/AR docs | PLOS/SciRep | **strong (10 links top fact)** |
| Sach-Gaurav field clone (2017/18), Veer Gaurav (2022), Gaurav 2.0 (Dec 2025) | NDTV/Indiatimes/Outlook + 2025 Hindi cluster | ICAR releases | Current Science | strong |
| NASF Phase-II + DBT projects (codes/budgets) | — | AR tables (CIRB-NEF-22-001; ₹450.58 L; DBT ₹14.27/13.67 L) | — | institutional-only |
| Awards: SAPI Fellow 2015/16, ISBD 2019, Nanaji Deshmukh 2019/20, IBOR 2021, Guraya oration 2026 | Nanaji award: Bhaskar/Jagran; IBOR registry | ICAR awardee list, CIRB news | — | mixed — 2 awards institutional-only (accepted warning) |
| Retirement 30 Apr 2025 | Amar Ujala | staff list, AR 2025 | — | 2–3 |

## 6. Gaps & unresolved
1. **Education chapter is thin** — no independent/archival record of the 1985/87/91 HAU degrees beyond a publisher bio; the Ph.D. thesis is absent from Krishikosh/Shodhganga (verified absent).
2. **No independent coverage for two awards** (SAPI Fellow, ISBD Distinguished Scientist) — issuer-institutional only.
3. **Internet Archive global outage** during the audit window: wayback-dependent verification is paused; 4 draft links show transient "unknown".
4. **Pre-1993 and family/early-life** have no independent coverage (BLP-prudent, but limits the "Early life" section).
5. **Nascent metric provenance split**: registry metrics (Scopus/Crossref h-index) are sourced to Vidwan; no independent bibliometric database audit.
6. **Agent-heavy review trail** — 33 agent-verified claims; a human spot-check is recommended before any external submission.

## 7. Verdict
**Pass with conditions — strong notability, sound identity discipline, improvable claim-level auditability.**
- Notability: comfortably beyond AfC threshold (15 significant independent origins + academic record), with no single-source dependence for core claims.
- Reputational risk: low — namesake rejection was systematic and documented; no litigation/controversy trail exists (verified empty).
- Readiness for an encyclopedia draft: **yes for facts whose claims carry quotes and independent/institutional sources**;
  the remaining risk is *evidentiary hygiene*, not substance.

### Recommended actions (priority order)
1. **Backfill L4 quotes** for approved-but-unquoted claims (≈73 of 85 approved), starting with BL  sensitive fields (birth, education, retirement) — mechanical, from the cited pages.
2. **Reconcile `human_verified`** — reset to real state (`identity_status`/`coverage_depth`) so the flag means something.
3. **Resolve the 5 `needs_source_verification` facts** (verify source identity → approve or drop).
4. **Add independent evidence for the two institutional-only awards**, or mark the award lines as issuer-sourced in the article text.
5. **Re-run wayback verification** when Internet Archive recovers (telemetry recheck policy already parks hosts).
6. **Human spot-check** of 10–15 agent-approved facts by opening their cited links (30 minutes) before publication.

*Prepared from session state: 476 sources · 284 claims · 85 approved · 185 fact clusters · QA 0 errors, 2 accepted warnings, 1 info.*
