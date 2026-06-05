# FirstLot local demo CLI

This demo path is local-file only. It does **not** import the API app, Supabase adapters, dotenv, or live client integrations.

## Run the fixture demo

```bash
python3 -m app.local_cli run \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --out /tmp/firstlot-demo \
  --generated-at 2026-06-03T23:00:00
```

## Validate CSVs before a local run

Client-test readiness starts with validation, not FIFO allocation. The CLI can
check local purchase lots and movement CSVs without writing artifacts:

```bash
python3 -m app.local_cli validate \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv
```

The JSON response includes `valid`, `summary`, `errors`, and `warnings`. Current
checks cover required columns, valid ISO dates, integer quantities, nonnegative
cost/freight fields, duplicate lot IDs, duplicate sale IDs, and positive sale
quantities.

`run` performs this validation by default and exits before writing output files
when validation fails. Use `--skip-validation` only as an explicit local/debug
override; do not use it for client-test readiness checks.

## Regenerate dashboard demo artifacts

Reviewers can refresh the checked-in dashboard demo output from the same safe local
fixture path with one command from the repo root:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py
```

That command rewrites the checked-in v1 failed-run artifacts in
`cogs-dashboard/src/demo-output/firstlot_demo/` and, by default, the v2 fixed-rerun
artifacts in `cogs-dashboard/src/demo-output/firstlot_demo_fixed/`. It verifies
that the expected files exist and the JSON parses. It is still local-file only:
fixture CSV input, deterministic timestamp, no `.env`, no Supabase/API imports,
and no live database writes.

To regenerate into temporary/reviewer directories instead of the checked-in demo
folders:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py \
  --out /tmp/firstlot-demo-v1 \
  --fixed-out /tmp/firstlot-demo-fixed
```

If only a custom fixed-rerun directory is needed, either provide `--fixed-out` or
use `--include-fixed-rerun` with the default fixed output:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py \
  --out /tmp/firstlot-demo-v1 \
  --fixed-out /tmp/firstlot-demo-fixed \
  --include-fixed-rerun
```

Expected artifacts:

- `cogs_summary.csv` and `cogs_summary.json`
- `cogs_detail.csv` and `cogs_detail.json` with SKU/month merchandise, shipping, total, and average cost columns
- `remaining_layers.csv` and `remaining_layers.json`
- `audit_trail.csv` and `audit_trail.json`
- `shortfalls.csv` and `shortfalls.json`
- `failed_sku_queue.csv` and `failed_sku_queue.json`

The fixture demonstrates:

- multi-lot FIFO consumption for `SKU-A`,
- remaining layer output for `SKU-B`,
- sale-to-lot audit rows,
- an explicit partial shortfall for `SALE-002`,
- a SKU/month failed-SKU queue row for fix/rerun triage,
- deterministic report timestamps via `--generated-at`.

## Reproducible reviewer check

Use this command before changing the local demo path or dashboard demo view:

```bash
make check-firstlot-demo
```

Equivalent direct command:

```bash
python3 scripts/check_firstlot_demo.py
```

The check is intentionally safe and reproducible:

- regenerates the FirstLot CSV/JSON artifacts into a temporary directory with `python3 scripts/regenerate_firstlot_demo_artifacts.py --out <tmp>`,
- verifies the expected artifact files exist and JSON parses,
- runs the dashboard smoke test for `/demo` with `npm test -- --runTestsByPath src/App.test.js --watchAll=false`,
- avoids `.env`, Supabase, API imports, production services, and live database writes.

Optional flags:

- `--out <dir>` writes regenerated artifacts to a chosen local directory,
- `--keep-out` keeps the temporary regenerated artifacts for inspection,
- `--skip-dashboard` runs only the fixture artifact regeneration check.

## Local month-close history, reopen, append, and rollback-plan workflow

The local CLI can also append an audit/history row for fixture-backed monthly close
runs. This stays local-file only and writes `month_history.csv` plus
`month_history.json` in the chosen output directory:

```bash
python3 -m app.local_cli run \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --out /tmp/firstlot-demo \
  --generated-at 2026-06-03T23:00:00 \
  --period 2026-05 \
  --note "initial May close"
```

Safety behavior for month history:

- a second run for the same `--period` is blocked by default,
- use `--reopen --note "..."` for an intentional fix/rerun of that period,
- use `--append-prior-month --note "..."` for an intentional append/reclose of a prior month,
- `python3 -m app.local_cli history --out /tmp/firstlot-demo` prints the local history,
- `python3 -m app.local_cli rollback-plan --out /tmp/firstlot-demo --period 2026-05` prints a read-only operator plan and performs no file deletes, restores, or live-data mutations.

## Failed-SKU fix/rerun queue workflow

After a run writes `failed_sku_queue.csv/json`, operators can review the local
queue, generate a non-mutating fix plan, rerun with corrected local input CSVs,
and gate completion on a clear queue.

Start with the intentionally short v1 fixture run:

```bash
rm -rf /tmp/firstlot-demo-rerun
python3 -m app.local_cli run \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --out /tmp/firstlot-demo-rerun \
  --generated-at 2026-06-03T23:00:00 \
  --period 2026-05 \
  --note "v1 local fixture run queues SKU-A shortfall"
```

Review the local queue and generate a read-only fix plan:

```bash
python3 -m app.local_cli failed-skus \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05

python3 -m app.local_cli fix-plan \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05 \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --note "add missing local lot and rerun"
```

The fix plan is JSON with `read_only: true`, `mutations_performed: []`, affected
SKUs/periods, minimum additional available units needed, and suggested rerun
arguments.

Then rerun the same month with the corrected local fixture and `--reopen`:

```bash
python3 -m app.local_cli run \
  --lots tests/fixtures/firstlot_demo/purchase_lots_fixed.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --out /tmp/firstlot-demo-rerun \
  --generated-at 2026-06-03T23:00:00 \
  --period 2026-05 \
  --reopen \
  --note "v2 fixed rerun clears SKU-A queue"
```

Finally, assert the fixed queue is clear:

```bash
python3 -m app.local_cli failed-skus \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05 \
  --assert-clear
```

`--assert-clear` exits non-zero while matching failed-SKU rows remain, making it
usable in a local smoke check or review script without touching live data. The
fixed rerun should print JSON with `"clear": true`, `"queue_record_count": 0`,
and `"total_shortfall_quantity": 0`.

## Safety boundary

Use this CLI for synthetic fixtures and local/demo outputs only. Do not wire it to live Supabase or Storage Standard data without a separate reviewed adapter and explicit dry-run/commit split.
