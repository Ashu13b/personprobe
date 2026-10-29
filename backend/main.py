"""FastAPI backend for personprobe — app wiring.

Route handlers live in backend/routes_research.py, backend/routes_draft.py, and
backend/routes_sessions.py; request models in backend/schemas.py; the session
store in backend/store.py. This module wires the app, mounts the static
frontend, and re-exports the public API names the frontend and tests use.
"""

from __future__ import annotations

import ipaddress
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .store import SESSIONS_DIR, _sessions, _wiki_statuses  # noqa: F401  (public state)
from .schemas import (  # noqa: F401  (public request models)
    IdentifyRequest,
    ResearchRequest,
    AddSourceRequest,
    AddDocumentFact,
    AddSourcedClaimRequest,
    VerifyClaimRequest,
    BatchVerifyClaimsRequest,
    AddSourcePaste,
    CrawlRequest,
    TargetedSearchRequest,
    DraftRequest,
    FindIdsRequest,
    RefreshPapersRequest,
    AssessSourceRequest,
    VerifySourceLevelRequest,
)
from .routes_research import (  # noqa: F401  (public route handlers)
    identify,
    research_start,
    add_source,
    add_document_fact,
    add_sourced_claim,
    verify_claim,
    batch_verify_claims,
    add_source_paste,
    deep_crawl,
    targeted_search_endpoint,
    auto_enrich_endpoint,
    article_proposal,
    get_session,
    verify_source,
    verify_source_level,
    assess_source,
    reject_source,
    skip_suggestion,
    find_researcher_ids_endpoint,
    refresh_papers_endpoint,
    fetch_from_browser,
    fetch_blocked,
    suggest_urls,
    research_router,
)
from .routes_draft import (  # noqa: F401
    draft_audit,
    generate_draft,
    draft_links,
    draft_preview,
    draft_qa,
    draft_verify,
    draft_router,
)
from .routes_sessions import (  # noqa: F401
    resume_session,
    list_sessions,
    delete_session,
    sessions_router,
)
from .routes_browser import (  # noqa: F401
    captcha_solved,
    last_captcha_solved,
    browser_router,
)
from .routes_forensics import forensics_router  # noqa: F401
from .routes_ops import ops_router  # noqa: F401

api_app = FastAPI(title="personprobe")
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3890", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
api_app.include_router(research_router)
api_app.include_router(draft_router)
api_app.include_router(sessions_router)
api_app.include_router(browser_router)
api_app.include_router(forensics_router)
api_app.include_router(ops_router)


# ── Unified App setup ───────────────────────────────────────────────────────
from contextlib import asynccontextmanager  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from browser_server import stop_browser, app as browser_app  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Remote browser thread is lazily initialized on demand via _dispatch
    yield
    # Clean up Xvfb/Playwright processes
    stop_browser()


# Create unified top-level app
app = FastAPI(title="personprobe-unified", lifespan=lifespan)

# Add global CORS middleware to support local Vite dev server proxies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Network access guard ────────────────────────────────────────────────────
# The server binds 0.0.0.0 (so localhost tooling and the Tailscale-reached UI /
# phone companion all work) but has no authentication, so it must refuse any
# client that is neither loopback nor inside the Tailscale CGNAT range. This is
# network-trust, not auth: because loopback is trusted, any SSRF that reaches
# localhost becomes full API access — the fetcher/checker/browser URL guards
# must stay in place. Relaxed to True by the test suite (see tests/conftest.py).
_TRUST_ALL_CLIENTS = False
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _client_is_trusted(host: str | None) -> bool:
    if _TRUST_ALL_CLIENTS:
        return True
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip in _TAILSCALE_CGNAT


class _TrustedNetworkMiddleware:
    """Reject HTTP/WebSocket requests from untrusted client addresses (pure ASGI)."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            client = scope.get("client")
            if not _client_is_trusted(client[0] if client else None):
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 1008})
                else:
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 403,
                            "headers": [(b"content-type", b"text/plain")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": b"Forbidden: client address not trusted",
                        }
                    )
                return
        await self.asgi_app(scope, receive, send)


app.add_middleware(_TrustedNetworkMiddleware)

# Mount sub-apps
app.mount("/api", api_app)
app.mount("/browser", browser_app)

# Serve compiled frontend React SPA statically
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.api_route("/", methods=["GET", "HEAD"])
    async def serve_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def serve_catchall(path: str):
        # Fallback to index.html for SPA client-side routing (React Router)
        return FileResponse(FRONTEND_DIST / "index.html")
