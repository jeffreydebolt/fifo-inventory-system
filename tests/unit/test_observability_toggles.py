import importlib
import sys
from typing import Dict

import pytest
from fastapi.testclient import TestClient

from api import settings


TOGGLE_ENV_VARS = [
    "ENABLE_PROMETHEUS",
    "ENABLE_SENTRY",
    "ENABLE_DEBUG_ENDPOINTS",
    "SENTRY_DSN",
]


def _reload_app() -> "module":
    """Reload api.app so settings toggles take effect."""
    if "api.app" in sys.modules:
        return importlib.reload(sys.modules["api.app"])
    return importlib.import_module("api.app")


def _load_app(monkeypatch: pytest.MonkeyPatch, env: Dict[str, str]):
    """Helper to set env vars, reset settings cache, and reload the app module."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    settings.reset_settings_cache()
    _clear_prometheus_metrics()
    return _reload_app()


@pytest.fixture(autouse=True)
def cleanup_settings(monkeypatch: pytest.MonkeyPatch):
    yield
    for key in TOGGLE_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    settings.reset_settings_cache()
    _clear_prometheus_metrics()
    _reload_app()


def _clear_prometheus_metrics():
    from prometheus_client import REGISTRY

    # Remove collectors registered by previous imports to avoid duplication errors.
    for collector in list(REGISTRY._collector_to_names.keys()):
        names = REGISTRY._collector_to_names.get(collector, set())
        if any(name.startswith("http_request") for name in names):
            try:
                REGISTRY.unregister(collector)
            except KeyError:
                pass


def test_default_toggles_enable_all_features():
    from api import app as app_module

    client = TestClient(app_module.app)
    assert client.get("/metrics").status_code == 200
    assert client.get("/debug/database").status_code == 200


def test_metrics_route_absent_when_disabled(monkeypatch: pytest.MonkeyPatch):
    app_module = _load_app(monkeypatch, {"ENABLE_PROMETHEUS": "false"})

    client = TestClient(app_module.app)
    assert client.get("/metrics").status_code == 404
    # Other endpoints should remain available
    assert client.get("/health").status_code == 200


def test_debug_endpoint_absent_when_disabled(monkeypatch: pytest.MonkeyPatch):
    app_module = _load_app(monkeypatch, {"ENABLE_DEBUG_ENDPOINTS": "false"})

    client = TestClient(app_module.app)
    assert client.get("/debug/database").status_code == 404
    assert client.get("/health").status_code == 200


def test_sentry_initializes_only_when_enabled(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_init(**kwargs):
        calls.append(kwargs)

    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.local/1")
    monkeypatch.setenv("ENABLE_SENTRY", "true")
    monkeypatch.setattr("sentry_sdk.init", fake_init)
    app_module = _load_app(monkeypatch, {})
    assert calls, "Expected Sentry init to be called when enabled"
    assert calls[0]["dsn"] == "https://example@sentry.local/1"

    calls.clear()
    monkeypatch.setenv("ENABLE_SENTRY", "false")
    monkeypatch.setattr("sentry_sdk.init", fake_init)
    app_module = _load_app(monkeypatch, {})
    assert not calls, "Sentry init should not be called when disabled"
