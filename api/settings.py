"""
Runtime configuration for the FIFO COGS FastAPI service.

Provides a central location for environment-derived toggles controlling
observability integrations (Prometheus metrics, Sentry, debug endpoints).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AppSettings:
    enable_prometheus: bool = True
    enable_sentry: bool = True
    enable_debug_endpoints: bool = True
    sentry_dsn: Optional[str] = None


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings(
        enable_prometheus=_env_bool("ENABLE_PROMETHEUS", True),
        enable_sentry=_env_bool("ENABLE_SENTRY", True),
        enable_debug_endpoints=_env_bool("ENABLE_DEBUG_ENDPOINTS", True),
        sentry_dsn=os.getenv("SENTRY_DSN"),
    )


def reset_settings_cache() -> None:
    """Clear cached settings (used in tests when environment changes)."""
    get_settings.cache_clear()
