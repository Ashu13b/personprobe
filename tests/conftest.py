"""Isolate every test's session store from the real sessions/ directory."""

import pytest

from backend import main, store
from engine import fetch_telemetry, public_records_atlas


@pytest.fixture(autouse=True)
def _isolated_sessions(tmp_path, monkeypatch):
    isolated = tmp_path / "sessions"
    isolated.mkdir(exist_ok=True)
    monkeypatch.setattr(store, "SESSIONS_DIR", isolated)
    monkeypatch.setattr(fetch_telemetry, "LOG_PATH", isolated / "fetch_telemetry.jsonl")
    # The public-records atlas merges user/agent-registered custom repositories
    # from a live, gitignored registry file; isolate it so a subject registered
    # in real use never leaks into a test's discovery output.
    isolated_data = tmp_path / "data"
    isolated_data.mkdir(exist_ok=True)
    monkeypatch.setattr(public_records_atlas, "REGISTRY_DIR", isolated_data)
    monkeypatch.setattr(
        public_records_atlas,
        "REGISTRY_FILE",
        isolated_data / "public_records_registry.json",
    )
    # TestClient's default client host is the string "testclient", not an IP, so
    # the network guard would 403 every request; trust all clients under test.
    monkeypatch.setattr(main, "_TRUST_ALL_CLIENTS", True)
    yield
