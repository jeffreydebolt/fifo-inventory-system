from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app


def test_canonical_app_endpoints():
    """Smoke check canonical FastAPI endpoints."""
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json().get("message") == "FIFO COGS API is running"

    for path in ("/health", "/healthz", "/metrics"):
        response = client.get(path)
        assert response.status_code == 200, f"{path} should be available"


def test_procfile_uses_canonical_app():
    procfile = Path("Procfile").read_text().strip()
    assert "uvicorn api.app:app" in procfile


def test_dockerfile_cmd_uses_canonical_app():
    dockerfile = Path("Dockerfile").read_text()
    assert "uvicorn api.app:app" in dockerfile
