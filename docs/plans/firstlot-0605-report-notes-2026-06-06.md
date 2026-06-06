# FirstLot 06:05 report notes — 2026-06-06

Branch: `autonomous/fifo-nightly-2026-06-06-cycle1`

## Safety confirmation

- Worked local/fixture-only.
- Did not read or source `.env`.
- Did not write Supabase/live DB, Storage Standard/client data, production APIs, or deploy.
- Generated smoke-run checks only under `/tmp` or system temp folders.

## What changed this cycle

- Added `client-smoke --json-out` so Jeff can save the exact machine-readable summary to a chosen local path while terminal output stays concise and operator-readable.
- Added clearer `client-smoke --expect-clear` terminal failure summary when failed SKUs remain.
- Added `missing_lot_request.csv` for client-smoke failed-SKU runs, ahead of the existing sandbox synthetic repair lot template, so repair work starts from source-backed lot/cost evidence rather than invented COGS.
- Updated weekend client CSV test docs with the recommended first command, `--json-out`, failed-SKU interpretation, and the new missing-lot request artifact.
- Preserved existing JSON stdout behavior when `--json-out` is not used, to avoid breaking scripts/tests.

## Verification run locally

- `python3 -m pytest tests/unit/test_client_smoke_runner.py -q` → 5 passed after `--json-out` work.
- `python3 -m pytest tests/unit/test_failed_sku_workflow.py tests/unit/test_client_smoke_runner.py -q` → 7 passed.
- `make check-firstlot-weekend` → `38 passed`; FirstLot local demo safe check passed; Jest `src/App.test.js` 4 passed. React Router/punycode deprecation warnings only.
- Manual safe smoke check:
  - `python3 -m app.local_cli client-smoke --lots tests/fixtures/firstlot_client_exports/sample_lots_client_shape.csv --movement tests/fixtures/firstlot_client_exports/sample_sales_client_shape.csv --out /tmp/firstlot-json-out-check --period 2025-09 --json-out /tmp/firstlot-json-out-check-summary.json --clean-output`
  - Result: period `2025-09`, total COGS `52.27`, failed SKU count `0`, JSON summary written under `/tmp`.

## Current usability

Jeff can now run `client-smoke` against raw client-shaped CSV copies and get:

- normalized strict FirstLot CSVs,
- month-close artifacts,
- close packet,
- full JSON summary at an explicit path,
- concise terminal summary,
- failed-SKU fix plan,
- source-backed `missing_lot_request.csv` when lots are missing,
- sandbox-only synthetic repair template clearly demoted below source-backed repair.

## Remaining queue

- Lane 3: sanitized September replay fixture for the exact uploaded CSV schema/shortfall class.
- Lane 4: local/demo UI command wrapper for the smoke runner.
- Lane 5: rerun/version diff summary.
- Lane 6: dangerous script inventory/quarantine plan only; do not move/delete scripts without Jeff approval.
