<!-- context-kit ARCH_MAP · v0.2.0 · generated 2026-09-20 15:17 UTC · sha 9455818 · host instance-20260819-0844 -->

# ARCH_MAP

Top-level directories — what each is for + which dirs it imports. Consult before adding a cross-directory import; flagged cycles are architectural smells.

## Directories
- `./` — Process launchers and local browser integration. → `engine/`
- `adapters/` — _(unset — add to `.context-kit/purposes`)_ → `engine/`
- `backend/` — FastAPI transport, session persistence, and workflow orchestration. → `./`, `adapters/`, `engine/`, `scripts/`
- `engine/` — Domain services for identity, discovery, extraction, classification, and evidence analysis. → `adapters/`
- `frontend/` — React presentation, client API adapters, and user-workflow interaction. → `backend/`
- `scripts/` — Operational CLI utilities and offline automation scripts. → `adapters/`, `backend/`, `engine/`
- `tests/` — Unit, integration, and regression test suites. → `./`, `adapters/`, `backend/`, `engine/`, `frontend/`, `scripts/`

## Cycles
- `adapters/` → `engine/` closes a cycle — consider breaking this edge
- `backend/` → `scripts/` closes a cycle — consider breaking this edge
- `engine/` → `adapters/` closes a cycle — consider breaking this edge
- `scripts/` → `backend/` closes a cycle — consider breaking this edge
