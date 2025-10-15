# FIFO Inventory System – Current Architecture

## System Overview
- Python-based brownfield platform for calculating cost of goods sold (COGS) across multiple tenants using FIFO rules.
- Mix of delivery surfaces: a FastAPI service (`api/`), a Click-powered CLI (`app/cli.py`), and many operational scripts for data cleanup and recovery.
- Core business logic lives in the `core/` package (dataclasses, FIFO engine, validators) and is reused by services such as the journaled calculator and safe processors.
- Primary datastore is Supabase Postgres. When credentials are missing, many pathways fall back to “demo mode” with in-memory caches or CSVs.

## Runtime Contexts
- **API Service (`api/`)** – A single canonical FastAPI application (`api/app.py`) exposes upload, run-execution, and diagnostics endpoints. Historic entrypoints (`app_simple*`, `app_minimal`) now delegate to this module for backward compatibility. Routes call lightweight services in `api/services/`.
- **CLI (`app/cli.py`)** – Orchestrates end-to-end COGS runs and rollbacks from the shell, producing CSV/TXT artefacts and relying on `JournaledCalculator`.
- **Automation Scripts (`root/*.py`, `services/*.py`)** – Large collection of one-off tools for data migration, validation, and debugging. Many bypass shared services and talk directly to Supabase or local CSVs.
- **Upload Pipeline (`services/intelligent_upload_pipeline.py`)** – Composes format detection, validation, previews, and quarantine handling for messy CSV imports.
- **Safe Processing (`services/fifo_safe_processor.py`, `services/error_recovery_manager.py`)** – Provides protective wrappers around FIFO logic to isolate bad SKUs and generate recovery artefacts.

## Major Components
- **`core/` (Domain layer)** – Pure-Python dataclasses, the FIFO engine (`fifo_engine.py`), and database DTOs (`db_models.py`). Uses type hints, logging, and minimal dependencies.
- **`services/` (Application services)** – Journaled calculator (creates/saves runs, snapshots, validations), tenant isolation helpers, Supabase adapter, quarantine workflow, and safe processors.
- **`api/` (Delivery layer)** – FastAPI routers for file uploads and run management. Persistence delegated to `api/services/supabase_service.py`, which currently stores uploads in Supabase when possible and otherwise in a process-wide cache.
- **`infra/`** – SQL migration snippets and deployment helpers.
- **`tests/`** – Unit tests target the FIFO engine and parity with historic calculators. Integration tests focus on safety rails and data parity; coverage of API routes is minimal.
- **`cogs-dashboard/` & backups** – Front-end assets and archived builds for a Netlify dashboard; not actively coupled to Python runtime but live in repo.

## Data Flow (Current State)
- **File ingestion** → `api/routes/files.py` validates CSV uploads, persists metadata via `supabase_service`, and caches raw data. Upload pipeline scripts offer richer handling outside the API.
- **Run execution (API path)** → `api/routes/runs.py` calls `supabase_service.process_fifo_with_database` which fetches inventory snapshot + uploaded sales data, runs a simplified FIFO routine, and writes run status back to Supabase (demo-mode when DB unavailable).
- **Run execution (CLI path)** → `app/cli.py` loads CSVs, instantiates `FIFOEngine` + `JournaledCalculator`, records inventory movements, summaries, and validation errors. Persistence depends on injected DB adapter (currently optional/None).
- **Rollback** → CLI invokes `JournaledCalculator.rollback_run`, which restores inventory from snapshots and invalidates COGS data in Supabase when wired up.
- **Quarantine & review** → Upload pipeline quarantines problematic rows and emits CSV exports for manual correction; reintegration tooling exists but is largely manual.

## Integrations & Infrastructure
- **Supabase Postgres** – Primary system of record (`inventory_snapshots`, `cogs_runs`, `uploaded_files`, etc.). Access via official `supabase-py` client and custom safe adapter.
- **Prometheus** – Metrics (`REQUEST_COUNT`, `REQUEST_DURATION`) exposed by `api/app.py` at `/metrics`.
- **Sentry** – Optional tracing/exception monitoring when `SENTRY_DSN` is configured.
- **Docker** – Python 3.11 slim image installs system deps (gcc, psql client) then runs `start.py` with Uvicorn. Procfile launches `python -m api.app`.
- **Environment** – `.env` loading via `python-dotenv`. Critical env vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SENTRY_DSN`, `ENVIRONMENT`, `APP_VERSION`, `PORT`.

## Observability & Operations
- Python `logging` configured across modules; CLI writes structured progress messages.
- Safe adapters capture detailed error categories, store recovery artefacts on disk (`snapshots/`, output dirs).
- Numerous manual scripts exist for migrations, cleanup, and anomaly detection (e.g., `check_*`, `rollback_*`, `debug_*`). They vary in safety; many expect direct environment access.
- Health endpoints: `/health`, `/healthz`, `/debug/database`, `/metrics`. Database diagnostics reinitialize Supabase client on demand.
- Observability toggles (loaded via `api/settings.py`) allow environments to disable Prometheus metrics (`ENABLE_PROMETHEUS`), Sentry initialization (`ENABLE_SENTRY` in combination with `SENTRY_DSN`), and debug endpoints such as `/debug/database` (`ENABLE_DEBUG_ENDPOINTS`). All default to enabled to preserve production behavior.

## Technical Debt & Known Issues
- **Legacy aliases** – Deprecated FastAPI entrypoints still exist as thin shims around `api/app.py`; downstream references should be updated so the aliases can eventually be removed.
- **Persistence gaps** – `JournaledCalculator` expects a DB adapter but defaults to `None`; API route fallbacks store uploads in process memory, losing data after restart.
- **Mixed calculation paths** – CLI uses full journaled engine while API route uses simplified pandas-based FIFO; parity is not guaranteed.
- **Dependency drift** – `click` and other runtime deps used in code but missing from `requirements.txt`. Several scripts assume packages beyond base requirements (e.g., `supabase_adapter_safe` uses JSON, pandas, interactive prompts).
- **Testing coverage** – Unit tests cover core FIFO logic, but API routes, Supabase integrations, and safe processors lack automated coverage.
- **Archived artefacts** – Large backups (`cogs-dashboard_PRODUCTION_BACKUP_*`, `fifo_production_outputs_backup_*`) live in repo and complicate navigation.
- **Operational risk** – Production safeguards rely on manual confirmation prompts and local snapshots; there is no centralized audit store for recovery outputs.
