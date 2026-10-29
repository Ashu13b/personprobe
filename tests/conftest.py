"""Isolate every test's session store from the real sessions/ directory."""

import pytest

from backend import main, store
from engine import fetch_telemetry


@pytest.fixture(autouse=True)
def _isolated_sessions(tmp_path, monkeypatch):
    isolated = tmp_path / "sessions"
    isolated.mkdir(exist_ok=True)
    monkeypatch.setattr(store, "SESSIONS_DIR", isolated)
    monkeypatch.setattr(fetch_telemetry, "LOG_PATH", isolated / "fetch_telemetry.jsonl")
    # TestClient's default client host is the string "testclient", not an IP, so
    # the network guard would 403 every request; trust all clients under test.
    monkeypatch.setattr(main, "_TRUST_ALL_CLIENTS", True)
    yield
