<!-- context-kit managed · >>> context-kit >>> <<< context-kit <<< -->
# AGENTS.md

Single source of truth for every agent in this repo. `CLAUDE.md`, `GEMINI.md`,
etc. just point here.

## 0. Always-loaded indexes
@CODE_MAP.md
@ARCH_MAP.md
@DEPS_MAP.md
@COMMANDS_MAP.md
@CONVENTIONS_MAP.md
@WORKFLOW.md
@ENV_MAP.md

`WORKFLOW` is the development protocol for this repo's rigor profile — follow it.
`DOCS_MAP` indexes existing docs by heading — load the full doc on demand.
`COMMANDS_MAP` lists the exact build/run/test commands — use them, don't guess.
`AGENT_KNOWLEDGE.md` holds intent/state/context — read it when the *why* matters.
`ROADMAP.md` holds shipped/next/out-of-scope — read it before proposing new work.

## 1. Discovery protocol (do this, not habit)
- Consult **CODE_MAP** for symbol/file location before Grep/Read. On a large repo
  it renders as a *router* (a line-budgeted subset of files); when the banner says
  router mode, find a symbol with `.context-kit/ck where <name>` and read a file's
  symbols with `.context-kit/ck show <path>` instead of assuming it lists everything.
- Consult **ARCH_MAP** before adding a cross-directory import — it shows the dir→dir
  dependency edges and flags cycles; write within the existing seams.
- Consult **DEPS_MAP** before assuming a package or env key exists.
- Consult **ENV_MAP** before assuming the runtime (OS, versions, this host).
- If the SessionStart banner says maps are stale, run `.context-kit/ck build`.

## 2. What this project is
PersonProbe is a local research workspace for resolving a person's identity,
collecting and verifying sources, checking Wikimedia status, and producing the
appropriate output: a new AfC draft, improvements to existing content, or a
research dossier.

### Architecture (what filenames don't tell you)
- Single unified server: `backend/main.py` app serves `/api`, mounts the
  `browser_server.py` Playwright app at `/browser`, and statically serves the
  compiled `frontend/dist`. `bash start.sh` builds the frontend then runs one
  uvicorn on port **3890**. The three-server 8001/7070 layout in `CLAUDE.md`
  is stale — trust `backend/main.py` and `start.sh`.
- No database. Sessions are JSON files in `sessions/` (gitignored); in-memory
  dicts mirror loaded work. The draft regression test uses a frozen fixture at
  `tests/fixtures/Prem_Singh_Yadav.json`, not the live session.
- Drafting is deterministic and server-owned: `adapters/wiki/draft.py` `render_draft` /
  `audit_profile` produce all wikitext. No code path may emit LLM-invented
  prose (the old `adapters/wiki/wikitext.py` LLM draft path was deleted for this reason).
- LLM: `engine/llm.py` `get_provider()` falls back real LLM API → coding agent
  (JSON jobs in `agent_jobs/`, answered by this agent via `pending_jobs()` /
  `answer_job()` in `engine/agent_llm.py`) → stub (only with
  `PERSONPROBE_LLM=stub`). Under stub,
  `extract_claims()` is a no-op — never fabricated; humans add facts via
  add-document-fact / add-sourced-claim. Details in `AGENT_KNOWLEDGE.md`.
- Claim workflow: source verified → claims suggested → human approves. Only
  explicitly approved claims enter wikitext; verifying a source does not put
  claims in the draft.

## 3. Commands
- Run the app: `bash start.sh` (builds frontend, serves unified app on :3890).
  It kills any process on 3890/8001/7070 first and sets `PERSONPROBE_HEADLESS=1`
  — don't run it against a server you want to keep alive.
- Frontend dev/build/typecheck: `cd frontend && npm run dev` / `npm run build` /
  `npm run typecheck` (`tsc --noEmit`).
- Tests: `pytest` from the repo root (imports resolve `backend/engine/adapters` as
  top-level packages from root). Single file: `pytest tests/test_draft.py`.
  `tests/conftest.py` auto-isolates every test with a tmp `SESSIONS_DIR` — the
  real `sessions/` is never touched by tests.
- Quality gate: `sh .context-kit/ck gate` (pyright, ruff, eslint, tsc, pytest,
  plus dependency/modularity guards; `standard` profile → warning, non-blocking).
  `--fast` runs typecheck+lint only, skipping the test suite.
- Rebuild maps: `.context-kit/ck build` — Check staleness: `.context-kit/ck check`.
  The pre-commit hook rebuilds and stages maps automatically.
- Phone companion UI & Scraping Bridge: the Android phone is directly connected via Tailscale (`100.72.202.86`). The OpenScrape `AgentServer` runs on port **`38765`** directly on the phone. All communication between VM agents and the mobile browser occurs directly over Tailscale WireGuard (`http://100.72.202.86:38765`). Zero background SSH tunnels, zero port orchestration (8888, 6901, 3890 reverse tunnels are completely removed).
- Web Scraping & Bot Walls (CRITICAL RULE FOR AGENTS):
  - **DO NOT curl `http://localhost:3890/browser/navigate`** for external web scraping. Port 3890 runs Playwright on the VM's Google Cloud datacenter IP (`130.210.59.249`), which is immediately blocked by Cloudflare (Ray ID), ResearchGate, and bot mitigation systems.
  - **NEVER tell the user "write links in scrap browser".**
  - **Always scrape via OpenScrape Mobile Browser Bridge**:
    ```bash
    python3 /home/ubuntu/Expeei/android-browser/phone_ctl.py <url>
    ```
    or in Python:
    ```python
    import sys
    sys.path.append("/home/ubuntu/Expeei/android-browser")
    from openscrape_client import MobileBrowserClient
    client = MobileBrowserClient()
    data = client.scrape(url)
    ```
    This navigates and extracts the DOM and cookies via the physical phone's Indian mobile carrier network, bypassing all bot walls.
  - If a CAPTCHA, login wall, or slider drag puzzle appears, run:
    ```bash
    python3 /home/ubuntu/Expeei/android-browser/phone_ctl.py solve <url>
    ```
    and ask the human to solve it on the phone screen.

## 4. Non-obvious rules
See `AGENT_KNOWLEDGE.md`. Keep it current — when you learn *why* something is
the way it is, or what was tried and rejected, write it there.

## 5. Development protocol
See @WORKFLOW.md — the loop is profiled (`light`/`standard`/`strict`). Don't
refactor opportunistically. Verify via the actual CLI/UI when possible.

## 6. Multi-agent coordination (baton)
This repo coordinates multi-agent work through the local `baton` layer (SQLite at
`../baton/baton.db`). Coordination is decoupled from git — work-in-progress, review
verdicts, and task queues live in baton; only approved, merged feature commits touch
main.
- **Roles**:
  - **Claude Code → `planner-reviewer`**: plans slices, breaks down work, opens tasks,
    audits submitted work out-of-band via `git diff main...<sha>`, records a verdict
    with `review`. Does not normally implement handed-off tasks.
  - **Antigravity / Cursor / Codex → `implementer`**: claims an open task, works on a
    dedicated feature branch in an **isolated git worktree** (never the main tree),
    commits the *why* in the commit body, runs tests, then `submit_for_review`.
- **Discovery / presence**: at session start each agent calls
  `hello(repo="/home/ubuntu/Expeei/wikimaker")`. Presence is keyed by that absolute
  repo path — an agent only sees peers and open tasks for **the same cwd**, and rows
  older than 180s are treated offline. The reply lists peers online + open tasks;
  `heartbeat()` keeps you visible. Implementers block on
  `cli.py watch --role implementer --repo /home/ubuntu/Expeei/wikimaker` to be woken
  when an `open`/`changes_requested`/`needs_info` event lands for this repo.
- **Auto-briefing on startup**: a baton `SessionStart` hook (`baton/presence_hook.py`)
  announces each agent's presence *and* injects a short briefing of this repo's
  actionable tasks for your role — so you enter already aware, no prompting needed.
- **Subscription + auto sidecar watcher**: a `.baton` marker at the repo root subscribes
  this repo to coordination. On entering a subscribed repo, the hook additionally injects a
  **repo-scoped, role-scoped reactive-loop directive**: the reviewer runs a background
  `watch --role reviewer --repo <this> --cursor-file <per-repo>` and acts on `submitted`
  events; the implementer follows its watch loop for this repo. Presence/`solo`
  are repo-scoped, so two subscribed agents here → coordinated dev, one → solo. Each session
  stays single-repo — no cross-repo contamination.
- **Lifecycle**: `open → claim → (needs_info?) → submitted → done | changes_requested`.
- **Solo is the normal fallback, not an error**: a peer is not always online. If
  `hello`/`heartbeat` reports `solo: true` (no implementer present for this repo),
  just do the work directly per @WORKFLOW.md — don't park it in an `open` task that
  nothing will claim.

