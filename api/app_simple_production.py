"""
Legacy production alias that now delegates to the canonical FastAPI app.
Prefer importing :mod:`api.app` directly.
"""
import os
import warnings

from .app import app  # re-export canonical application

warnings.warn(
    "api.app_simple_production is deprecated; use api.app instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.app:app", host=host, port=port, log_level="info")
