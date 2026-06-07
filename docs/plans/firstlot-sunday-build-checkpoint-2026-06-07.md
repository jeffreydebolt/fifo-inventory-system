# FirstLot Sunday Inventory + Amazon Mock Build Checkpoint — 2026-06-07

Timestamp: 2026-06-07 morning MT

Branch: `autonomous/firstlot-sunday-ui-amazon-mock`

Base before Sunday work: `b10763f5 feat: add FirstLot local management summaries`

## Product direction

FirstLot should build its own focused inventory/onboarding/planning layer rather than cloning a full ERP.

Reference tools reviewed:

- ERPNext: best FIFO valuation / stock ledger / reconciliation reference; do not fork due GPL/heavy ERP scope.
- InvenTree: best permissive inventory UX/API reference; possible experimental fork only, not production base.
- Odoo: polished inventory UX reference; do not fork due weight/licensing/ecosystem complexity.
- Amazon SP-API references: use direct SP-API libraries/samples when live connector work is explicitly approved.

## What shipped locally on this branch

### 1. Operator-quality validation guidance

Commit: `431ed35c feat: add operator validation guidance`

Added more product-quality validation issue metadata while preserving existing validation fields:

- severity
- title
- details
- suggested_action
- blocking

Added safe cross-file checks:

- movement SKU missing from purchase lots
- sale date before first received lot for SKU

Added `validate --human` for operator-readable validation output.

Added validation issue / next-action content to `client_smoke_summary.md`.

### 2. Mock Amazon onboarding workflow

Commit: `02b81c77 feat: add mock Amazon onboarding workflow`

Added deterministic fixture-backed Amazon onboarding architecture:

- `core/connectors/amazon_sp_api_contract.py`
- `core/connectors/amazon_sp_api_mock.py`
- `core/amazon_onboarding.py`
- `python3 -m app.local_cli amazon-onboarding-mock ...`
- Amazon fixture files under `tests/fixtures/amazon_sp_api_mock/`
- unit tests for connector, onboarding payload, and CLI

Safety proof fields are present:

- `connector_mode: mock`
- `credentials_loaded: false`
- `live_api_calls_performed: []`
- `mutations_performed: []`

This is intentionally not a live Amazon connector.

### 3. Polished Inventory Command Center demo

Commit: `8f211fdf feat: polish FirstLot inventory command center demo`

Changed the demo product frame from FIFO-only toward:

- `FirstLot Inventory Command Center`
- mock Amazon onboarding timeline
- inventory tracking table
- planning/replenishment table
- FIFO day 0 proposal concept
- explicit local/demo/no Seller Central/no SP-API/no DB-write safety copy

Preserved the downstream FIFO COGS, failed SKU, fixed rerun, history, and rollback-plan sections.

### 4. Build plan saved

Saved durable plan:

- `docs/plans/firstlot-sunday-inventory-amazon-ui-build-plan-2026-06-07.md`

Historical overnight checkpoint kept/resolved:

- `docs/plans/firstlot-0205-checkpoint-2026-06-07.md`

## Verification run

Targeted Python tests:

```bash
python3 -m pytest tests/unit/test_csv_validation.py tests/unit/test_local_csv_cli.py tests/unit/test_client_smoke_runner.py tests/unit/test_amazon_sp_api_mock_connector.py tests/unit/test_amazon_onboarding.py tests/unit/test_local_cli_amazon_onboarding.py -q
```

Result:

```text
22 passed in 0.66s
```

Dashboard tests/build:

```bash
cd cogs-dashboard
CI=true npm test -- --watchAll=false
npm run build
```

Result summary:

```text
PASS src/App.test.js
Tests: 4 passed
Compiled successfully.
```

Repo-owned safe checks:

```bash
make check-firstlot-demo
make check-firstlot-weekend
```

Result summary:

```text
FirstLot local demo safe check passed.
No staged client/live data detected.
45 passed in 1.87s
PASS src/App.test.js
Tests: 4 passed
FirstLot local demo safe check passed.
```

Warnings observed but non-blocking:

- React Router v7 future flag warnings
- Node `punycode` deprecation warning
- Browserslist/caniuse-lite stale data warning during production build

## Safety confirmation

No `.env` reads.
No live Amazon SP-API calls.
No live DB writes.
No Supabase/API live write path executed.
No Storage Standard/client data mutation.
No real client CSVs committed.
No push / no PR opened.

## Later Sunday continuation

Added a deeper day-zero readiness pass after the checkpoint:

- mock purchase-lot guidance now includes supported lot IDs and draft receipts inside the rollback period,
- Amazon onboarding payload now emits `rollback_reconstruction`, `source_support_ratio`, source document guidance, and a day-zero readiness checklist,
- `/demo` now shows readiness gates, source support percentage, and a per-SKU backward reconstruction table,
- deterministic tests cover day-zero readiness fields, unmatched inventory document guidance, supported lot IDs, and rollback estimates,
- new doc: `docs/plans/firstlot-day-zero-readiness-draft-2026-06-07.md`.

This continuation remains fixture/local/mock-only.

## Remaining product questions for Jeff review

1. FIFO day 0: should day 0 be the earliest date where current in-stock can be reconciled to source-backed lots/freight, with exceptions shown as blockers?
2. Amazon history: how far back should we try to pull sales/orders/reports before declaring the rollback confidence low?
3. Non-Amazon warehouses: should non-Amazon counts be treated as day-0 snapshot inputs only, or should they have movement history too?
4. Source-backed lots/freight: what is enough support to accept a lot/freight record during onboarding?
5. Live connector: when Jeff approves Amazon SP-API work, build OAuth/auth/read-only pulls as a separate reviewed branch.
