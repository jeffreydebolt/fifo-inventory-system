# FirstLot overnight build notes — 2026-06-05 06:05

Branch: `autonomous/fifo-nightly-2026-06-04-early`

## Safety scope

- Work stayed fixture/local-only.
- No `.env` files read or sourced.
- No Supabase/live database writes.
- No Storage Standard/client data mutation.
- No production deploy.

## What changed in this checkpoint

- Added SKU-level COGS detail artifacts (`cogs_detail.csv/json`) with merchandise, freight/shipping, total, and average cost fields.
- Added local failed-SKU workflow commands:
  - `failed-skus` to review generated queue rows or assert a queue is clear.
  - `fix-plan` to print a read-only operator fix/rerun packet.
- Added fixed-rerun fixture artifacts under `cogs-dashboard/src/demo-output/firstlot_demo_fixed/`.
- Updated `/demo` to tell the actual FirstLot operator story: upload purchase lots CSV, upload sales CSV, run selected month, review SKU costs, fix failed SKUs/rerun, preserve close history.
- Updated docs with exact local commands and PR-readiness handoff.

## Verification run

- `python3 -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py -q` → `16 passed in 0.49s`.
- `make check-firstlot-demo` → passed, including artifact regeneration and dashboard Jest smoke.
- `cd cogs-dashboard && npm test -- --runTestsByPath src/App.test.js --watchAll=false` → 1 suite passed / 3 tests passed. Only existing React Router future-flag and Node `punycode` deprecation warnings appeared.
- `python3 scripts/regenerate_firstlot_demo_artifacts.py --out /tmp/firstlot-demo-check --fixed-out /tmp/firstlot-demo-fixed-check` → verified v1 12 artifacts and v2 fixed 14 artifacts.
- `python3 -m app.local_cli fix-plan --out cogs-dashboard/src/demo-output/firstlot_demo --period 2026-05 --lots tests/fixtures/firstlot_demo/purchase_lots.csv --movement tests/fixtures/firstlot_demo/movement.csv` → emitted read-only JSON with `mutations_performed: []`, SKU-A shortfall guidance, rerun command, and completion check command.

## PR #3 context inspected

PR #3 (`epic/unified fastapi runtime`) is closed, not merged. It is unrelated to this fixture/local FirstLot lane.

## Remaining low-risk build queue

- Add pre-run CSV validation fixtures/CLI command.
- Add a deterministic close packet (`close_packet.json/md`) per local run.
- Add browser/local fixture file-selection prototype without live API calls.
- Later: local API wrapper and mock connectors only; no live adapters until approved.
