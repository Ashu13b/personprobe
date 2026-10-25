<!-- context-kit ARCH_MAP · v0.2.0 · generated 2026-10-25 10:47 UTC · sha fe160fd · host instance-trading-bot-restored -->

# ARCH_MAP

Top-level directories — what each is for + which dirs it imports. Consult before adding a cross-directory import; flagged cycles are architectural smells.

## Directories
- `./` — Process launchers and local browser integration. → `engine/`
- `adapters/` — Wikipedia AfC and Hindi draft rendering, verification, and diffing. → `engine/`
- `backend/` — FastAPI transport, session persistence, and workflow orchestration. → `./`, `adapters/`, `engine/`, `frontend/`, `scripts/`
- `engine/` — Domain services for identity, discovery, extraction, classification, and evidence analysis. → `adapters/`
- `frontend/` — React presentation, client API adapters, and user-workflow interaction. → `backend/`, `engine/`
- `scripts/` — Operational CLI utilities and offline automation scripts. → `adapters/`, `backend/`, `engine/`
- `tests/` — Unit, integration, and regression test suites. → `./`, `adapters/`, `backend/`, `engine/`, `frontend/`, `scripts/`

## Cycles
- `adapters/` → `engine/` closes a cycle — consider breaking this edge
- `backend/` → `frontend/` closes a cycle — consider breaking this edge
- `backend/` → `scripts/` closes a cycle — consider breaking this edge
- `engine/` → `adapters/` closes a cycle — consider breaking this edge
- `frontend/` → `backend/` closes a cycle — consider breaking this edge
- `scripts/` → `backend/` closes a cycle — consider breaking this edge
