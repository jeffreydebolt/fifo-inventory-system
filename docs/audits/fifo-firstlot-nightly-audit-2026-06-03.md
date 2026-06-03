# FIFO / FirstLot nightly audit and roadmap — 2026-06-03

Scope: full-scale read-only audit before normal autonomous building. This repo has live/client-derived Supabase and Storage Standard history, so the audit prioritized safety, local-only tests, and separable open-source FIFO engine work.

## Safety boundary followed

- Stayed on local branch `autonomous/fifo-nightly`.
- Did not push, open PRs, source `.env`, or run mutation scripts.
- Confirmed credential-like files exist without reading contents: `env`, `src/env`, and `cogs-dashboard/.env` exist; repo-root `.env` and `cogs-dashboard_PRODUCTION_BACKUP_20250825/.env` were absent.
- Treated scripts matching `upload_*`, `delete_*`, `rollback_*`, `restore_*`, `migrate_*`, `clean_*`, `fix_*anomal*`, and Supabase write paths as source-only.

## Repo/branch state

- Current branch: `autonomous/fifo-nightly`.
- Working tree was clean before this audit document was written.
- Recent local autonomous commit: `f55a599a chore: add autonomous FIFO safety guardrails`.
- Main branch head: `e1d123b feat: Complete Step 5 ops scripts`.
- Remote PR #3 branch exists locally as `origin/epic/unified-fastapi-runtime` at `1c27a468 Fix CI: upgrade pandas to 2.2.2`.

## Existing UI audit

### Current `cogs-dashboard/`

What exists:

- React app with `LoginPage` and `UploadPage` routes.
- Upload page supports selecting purchase-lot and sales CSV files.
- Hard-coded API base: `https://api.firstlot.co`.
- Hard-coded upload tenant: `test_user_9999` with comment “Test tenant - NOT your real data”.
- UI can download templates from `/api/v1/files/templates/{type}` and post files to:
  - `/api/v1/files/lots`
  - `/api/v1/files/sales`
  - `/api/v1/runs`

What works / should be retained:

- Basic product shape is right: upload lots, upload sales, run/process COGS.
- Simple progress/status messaging and required-field hints are useful.
- Current UI is good as a prototype/reference for a future paid convenience app.

What is brittle / should be rewritten later:

- Hard-coded live API URL makes local/offline development difficult and increases accidental production-touch risk.
- Hard-coded test tenant is safer than a real tenant but still couples UI behavior to server assumptions.
- “Process vs Inventory” calls a remote API; it is not suitable for autonomous tests.
- Date, sales, and lot field expectations are narrow and not gentle enough for messy Amazon/Shopify/vendor files.
- UI should not be the next primary build target; CLI-first engine will reduce risk and clarify the product contract.

### `cogs-dashboard_PRODUCTION_BACKUP_20250825/`

- Contains an older/more complete UI with AuthContext, Supabase browser client, runs service, templates, and upload pages.
- Useful as reference for future paid app patterns: auth, tenant-aware runs, template download, dashboards.
- Should not be resurrected blindly because it includes direct Supabase auth coupling and vendored `node_modules`/build artifacts.

## Existing FIFO logic audit

### Pure/core engine

Files reviewed:

- `core/models.py`
- `core/fifo_engine.py`
- `tests/unit/test_fifo_engine.py`
- `tests/unit/test_parity_with_legacy.py`

Current strengths:

- `core/` already contains pure dataclass models and FIFO logic with no Supabase dependency.
- `FIFOEngine.process_transactions()` copies input lots, processes transactions, returns COGS attributions and final inventory snapshot.
- Tests cover simple FIFO allocation, multi-lot allocation, multiple SKUs, insufficient inventory, sales before receipt, return behavior, and COGS summaries.
- Remaining layers are represented as the final `InventorySnapshot`.
- Audit trail is represented by `COGSAttribution` with per-lot allocations.

Important issues / design risks:

- Return handling currently processes all returns before all sales, regardless of transaction date. That can be wrong for daily mode and month sequences. One existing test logs an error because a return is applied before the sale that created available room in the lot.
- Shortfalls currently produce validation errors and skip the entire sale. This is safe because it does not invent cost, but the product needs clearer shortfall output for user workflows.
- `InventorySnapshot.get_available_lots()` sorts only by `received_date`; deterministic tie-breaking should add `lot_id` or source row order.
- COGS summary month format is rigidly `YYYY-MM`, which is deterministic but not ingestion-friendly.
- Purchase lot model includes unit price and freight per unit but not tariff, source document, vendor, warehouse, PO/invoice reference, landed-cost allocation basis, or notes.
- Existing attributions are good but not yet exported through a stable CLI/schema.

### Legacy/Supabase variants

The repo has many root and `src/` FIFO variants, including Supabase-coupled calculators and uploaders. Patterns observed:

- `fifo_calculator_supabase*.py`, `fifo_calculator_robust*.py`, and `fifo_calculator_validated.py` initialize Supabase clients and can update remaining quantities.
- `supabase_lot_uploader.py` variants insert lots into Supabase.
- These are useful as legacy reference but are not safe autonomous execution targets.
- The open-source engine should not depend on these modules or on `.env`/Supabase.

## Existing functionality/tests audit

Safe tests run locally:

```text
python3 -m unittest tests.unit.test_fifo_engine
....Error processing return: Cannot return 20 units to lot LOT001: would exceed original quantity
...
----------------------------------------------------------------------
Ran 7 tests in 0.001s

OK
```

Blocked/failed safe tests:

```text
python3 -m unittest tests.unit.test_parity_with_legacy
ModuleNotFoundError: No module named 'pandas'
FAILED (errors=1)
```

Frontend build check:

```text
cd cogs-dashboard && npm run build
Error: Cannot find module './lib/parse'
Require stack includes cogs-dashboard/node_modules/cross-spawn/index.js
Node.js v25.5.0
```

Interpretation:

- Pure engine unit tests are runnable without database access and pass, but one test exposes the return-ordering bug via logged error.
- Pandas-dependent tests need a venv/uv-managed dependency setup before they can be treated as nightly-safe.
- Frontend dependencies are present but broken; likely `node_modules` drift/corruption. Do not spend nightly effort here until core engine/CLI stabilizes.

## PR #3 audit: `epic/unified-fastapi-runtime`

Diff against `main`:

- 32 files changed, 1015 insertions, 1401 deletions.
- Adds `api/settings.py` and FastAPI runtime/observability tests.
- Adds docs/stories/QA gates for unified runtime entrypoints and observability toggles.
- Modifies `api/app.py`, `api/app_minimal.py`, `api/app_simple.py`, `api/app_simple_production.py`, `start.py`, deployment files, and `requirements.txt`.
- Deletes or empties multiple ops scripts, including backup/key/check/metrics scripts and rollback/rerun scripts.

Recommendation:

- **Cherry-pick ideas, do not merge wholesale now.**
- Salvage candidates:
  - canonical API entrypoint concept,
  - `api/settings.py` / environment-driven observability toggles,
  - launcher smoke tests,
  - docs/stories as architectural references.
- Discard/defer candidates:
  - wholesale deletion of ops scripts until Jeff explicitly reviews operational impact,
  - runtime refactor before engine/CLI boundaries are stable,
  - any CI conclusions based on stale/closed PR status.
- PR #3 is directionally useful for the future paid API layer, but the immediate autonomous lane should keep focusing on pure engine + CLI because that is safer and unlocks open-source value.

## Production/client-data risk register

High-risk execution targets observed:

- Upload scripts: `upload_lots_with_env.py`, `upload_june_lots.py`, `upload_july_missing_lots.py`, `upload_july_lots.py`, `upload_aug_lots_fixed.py`, `upload_aug_lots.py`, Supabase lot uploader variants.
- Rollback/restore/migration scripts: `rollback_may_2025.py`, `rollback_july_2025.py`, `restore_original_july_consumption.py`, `migrate_existing_data.py`, shell rollback scripts.
- Cleanup/fix scripts: `scripts/clean_golden_sales.py`, `fix_inventory_anomalies.py`.
- Discovery/interaction scripts that may query live data: `interact_with_client_data.py`, `find_real_client_data.py`, `find_all_existing_data.py`, `discover_all_tables.py`, `show_actual_inventory.py`, `test_supabase_connection.py`.
- Frontend upload UI posts to a live API base by default.
- Credential-like files exist in the repo tree (`env`, `src/env`, `cogs-dashboard/.env`) and must not be read or printed.

Safety recommendation:

- Add/maintain a clear README/guardrail that the open-source CLI must run entirely from local CSV fixtures and must never import Supabase modules.
- Consider quarantining legacy live-data scripts under a `legacy_live/` or `ops_live_do_not_run/` path once Jeff approves structural cleanup.

## Product roadmap: scalable path

### Free/open-source layer

Goal: deterministic FIFO costing engine + CLI.

Minimum CLI outputs:

- Month-end COGS by SKU/month.
- Remaining inventory layers by SKU/lot/date/cost.
- Audit trail by sale/movement and lot allocation.
- Shortfall report for missing/insufficient lots.

Near-term architecture:

- Keep `core/` pure: models, engine, validators, serializers.
- Add `cli/` or package entrypoint for CSV loading/output.
- Add tiny synthetic CSV fixtures under `tests/fixtures/` or `examples/`.
- Keep database adapters and UI outside the engine.

### Paid convenience app

Paid value should be convenience, storage, integrations, and guidance:

- Browser uploads and saved mappings.
- Amazon/Shopify normalization.
- Client/company workspace and history.
- Month-end close checklist.
- CSV/Xero/QBO export support.
- AI-assisted PO/invoice extraction and freight/tariff clarification workflow.

## Future feature planning notes

- Flexible/gentle date parsing: accept common date formats at ingestion, normalize internally to ISO dates, warn instead of surprising users.
- Purchase lot builder: fields should include SKU, received date, original quantity, remaining quantity, unit cost, freight, tariff, vendor, PO/invoice/source document, warehouse, and notes.
- AI PO document extraction: extract SKU/date/quantity/cost and ask users to resolve ambiguous fields; never silently allocate freight/tariff without a documented basis.
- Freight/tariff allocation: support per-unit, by quantity, by cost, by weight/dimensions later; require user clarification when basis is missing.
- Amazon API pull: future paid integration for movement/sales data; keep transform layer separate from FIFO engine.
- Shopify API pull: future paid integration for non-Amazon orders/movements.
- Daily vs monthly FIFO: engine should support event ordering for daily mode and monthly close summaries for accountants.
- Quarterly valuation mode: should generate remaining layer valuation, exception checklist, and cost-change review.
- Sales imply inventory but lots missing: never invent cost; produce explicit shortfall records with likely causes and resolution workflow.

## Recommended next autonomous steps

1. Create small synthetic CSV fixtures for purchase lots and sales/movements.
2. Add a local-only CLI test that exercises a complete month-end run and asserts COGS, remaining layers, and audit trail output.
3. Fix return sequencing in `FIFOEngine` by processing all transactions in date order while preserving deterministic behavior.
4. Add explicit `Shortfall` output model instead of only storing validation errors.
5. Add deterministic sort tie-breakers for lots and transactions.
6. Only after CLI is stable, revisit PR #3 for API/runtime cherry-picks.
