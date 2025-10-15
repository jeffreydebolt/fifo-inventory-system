# Tech Stack Reference

## Application Layer
- **Language**: Python 3.11 (Docker base image `python:3.11-slim`).
- **Web framework**: FastAPI 0.104.1 (REST APIs, OpenAPI docs).
- **CLI framework**: Click (used in `app/cli.py`, not yet pinned in requirements).
- **Task runners / scripts**: Plain Python scripts leveraging pandas, Supabase client, and custom services.

## Core Libraries
- **Pandas 2.1.4** – CSV ingestion, normalization, and FIFO calculations in API/service layer.
- **Pydantic 2.5.2** – Request/response schemas for FastAPI endpoints.
- **Supabase-py 2.8.0** – Database access to Supabase Postgres.
- **Python-dotenv 1.0.0** – Loads `.env` for local development.
- **Sentry SDK 1.39.2** – Optional tracing/error reporting (`sentry-sdk[fastapi]`).
- **Prometheus Client 0.19.0** – HTTP metrics exposed at `/metrics`.
- **Uvicorn 0.24.0** – ASGI server (run via `uvicorn[standard]` extras).

## Infrastructure & Deployment
- **Database**: Supabase (hosted Postgres). Tables referenced include `inventory_snapshots`, `cogs_runs`, `uploaded_files`, and quarantine-related tables.
- **Containerization**: Dockerfile builds single-stage image, installs GCC + `postgresql-client`, then executes `python start.py`.
- **Process management**: `Procfile` declares `web: cd /app && python -m api.app` for PaaS deployment (e.g., Heroku/Railway).
- **Observability**: Prometheus metrics, Sentry tracing, Python logging (INFO level). Diagnostic endpoints `/health`, `/healthz`, `/debug/database`.

## Front-End & External Assets
- **cogs-dashboard** – Netlify-hosted React dashboard (source & backups included for reference).
- **Static artefacts** – CSV samples, golden data sets, and backup exports stored under `golden/`, `fifo_test_outputs/`, `logs/`, etc.

## Notable Gaps
- `click` and other helper libraries (e.g., `tabulate` in some scripts) are used but missing from `requirements.txt`.
- Several scripts rely on optional imports (Supabase admin client, Google Sheets API) that must be installed manually when needed.
