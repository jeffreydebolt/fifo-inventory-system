"""
Deprecated ultra-minimal alias kept for compatibility with older deployments.
All new usage should import :mod:`api.app` instead.
"""
import os
import warnings

from .app import app  # re-export canonical application

warnings.warn(
    "api.app_minimal is deprecated; use api.app instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port, log_level="info")
