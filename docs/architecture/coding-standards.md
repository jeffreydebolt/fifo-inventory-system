# Coding Standards (Current State)

- **Python 3.11 runtime** – Codebase assumes modern typing (type hints, `dataclasses`, `Enum`) and uses f-strings everywhere.
- **Domain models** – Business entities live in `core/models.py` & `core/db_models.py` as dataclasses. New logic should extend those modules rather than duplicating lightweight structs.
- **Logging** – Use the module-level `logging.getLogger(__name__)`; core and services log at INFO with contextual messages. CLI adds file handlers when writing artefacts.
- **Error handling** – Favor explicit exceptions with descriptive messages. Safe-processing modules record issues through `ErrorRecoveryManager` instead of swallowing errors.
- **DataFrames** – Pandas is the default tool for CSV normalization. Preserve column casing encountered in source files and document any normalization in helper classes (e.g., `tests/unit/csv_normalizer.py`).
- **Tenant isolation** – Wrap multi-tenant work in `TenantContext` and use `TenantService` helpers for validation. Avoid hardcoding tenant IDs in shared code.
- **FastAPI patterns** – Define request/response models in `api/models.py`, expose routers from `api/routes/*`, and keep services in `api/services/*`. Side effects (Supabase calls) should stay in services.
- **CLI/Script ergonomics** – Scripts should accept parameters (env vars or argparse/click) instead of editing constants inline. Reuse `JournaledCalculator` for runs/rollbacks when possible.
- **Testing** – Unit tests rely on pytest and helper fixtures in `tests/unit`. Mirror new FIFO logic with tests comparing against known-good calculators or golden CSVs. Integration tests often expect real Supabase credentials; guard them behind env checks.
- **Operational artefacts** – Write outputs to clearly named directories (timestamped when long-running) and avoid overwriting raw source files. Keep recovery or quarantine exports in dedicated folders.

