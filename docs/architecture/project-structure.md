# Project Structure Guide

## Root
- `app/` – Click CLI entrypoint for executing FIFO runs and rollbacks.
- `api/` – Canonical FastAPI application (`app.py`), legacy aliases (`app_simple*`, `app_minimal`) that now import the canonical app, configuration helpers (`settings.py`), routers (`routes/`), and API-specific services/models.
- `core/` – Domain models, FIFO engine, validators, and DB DTOs.
- `services/` – Application services (journaled calculator, tenant isolation, intelligent upload pipeline, safe processors, Supabase adapters).
- `infra/` – Database migrations and deployment helpers.
- `tests/` – Pytest suites (unit + integration) plus utility fixtures.
- `docs/` – Product/design docs and generated architecture references (this directory).
- `scripts/`, `check_*.py`, `debug_*.py`, `rollback_*.py`, etc. – Operational utilities for data cleanup, migrations, and investigations; many expect Supabase access.
- `cogs-dashboard/` & `cogs-dashboard_PRODUCTION_BACKUP_*` – React dashboard source and archived builds.
- `fifo_*` modules (`fifo_calculator_supabase.py`, `fifo_calculator_enhanced.py`, etc.) – Legacy and experimental calculators retained for parity comparisons.
- `logs/`, `golden/`, `fifo_test_outputs/`, `demo_*`, `quarantine/` – Sample data, processing outputs, and diagnostics.

## Supporting Assets
- `Dockerfile`, `Procfile`, `build.sh`, `README_*` – Deployment automation and environment setup notes.
- `.bmad-core/` – BMAD agent configuration, checklists, and workflow templates.
- `requirements.txt` – Python dependencies for API/CLI runtime.
- `env/`, `full_2_years_both_warehouses/`, `test_*` folders – Environment-specific data snapshots used during investigations.
