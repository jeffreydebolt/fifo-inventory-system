# FirstLot local demo CLI

This demo path is local-file only. It does **not** import the API app, Supabase adapters, dotenv, or live client integrations.

## Run the fixture demo

For Jeff/reviewer handoff, run the whole local demo packet generator from the repo root:

```bash
make firstlot-demo-run
```

It writes the v1 failed-queue packet to `/tmp/firstlot-demo-v1`, the v2 fixed-rerun packet to `/tmp/firstlot-demo-fixed`, and prints the `/demo` dashboard URL to open after `npm start`. The target is local-file only and uses synthetic fixtures.

For the lower-level single-run CLI command:

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

## Generic client-test fixture workflow

For the concrete weekend packet, use
[`docs/firstlot-weekend-client-csv-test-packet.md`](firstlot-weekend-client-csv-test-packet.md).
It includes CSV schemas, copy/paste commands, artifact review steps, failed-SKU
rerun instructions, and stop conditions for trying another client's CSV exports
without committing or mutating client data.

For a second synthetic client-style fixture, use the wrapper below. It expects a
local folder containing `purchase_lots.csv` and `movement.csv`, validates those
files, runs FIFO into a local output directory, writes a close packet, and can
assert that the failed-SKU queue is clear. It is still local-only and does not
read `.env`, import Supabase/API code, mutate live data, or deploy anything.

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir tests/fixtures/firstlot_second_synthetic_client \
  --out /tmp/firstlot-second-synthetic-client \
  --period 2026-06 \
  --expect-clear \
  --clean-output
```

Expected synthetic result: validation passes, failed-SKU queue is clear, total
COGS is `723.00`, remaining inventory value is `485.50`, and artifacts are written
under `/tmp/firstlot-second-synthetic-client`.

To try another local CSV export this weekend, copy/export files into a folder with
these exact filenames and run the same command with a temp output path:

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir /path/to/local-client-fixture \
  --out /tmp/firstlot-client-test \
  --period 2026-06 \
  --clean-output
```

Add `--expect-clear` when you want the command to fail unless all sales were fully
matched. If the same output folder/period is intentionally rerun without cleaning,
add `--reopen` so local month history records it as a rerun instead of blocking a
duplicate close. `--clean-output` only deletes temp-directory outputs.

## Dashboard local client-test file-selection flow

The `/demo` page includes a browser-only client-test selector backed by
`cogs-dashboard/src/demoData.js`. It does not read local files directly, upload
CSV content, call APIs, or mutate any live/client records. It only changes React
page state between known fixture packets so reviewers can see the intended flow:

1. choose a fixture packet,
2. confirm purchase lots CSV and sales CSV paths,
3. confirm selected month and validation/run status,
4. inspect failed-queue and close-packet artifact locations,
5. continue to the month-close workflow, SKU costs, failed queue, fixed rerun, and
   history sections.

Current fixture choices are the v1 FirstLot demo with one failed SKU, the v2 fixed
rerun with a clear queue, and the second synthetic client-style fixture. The UI
smoke test asserts this section is visible and that changing the selector still
makes no `fetch` calls.

## Regenerate dashboard demo artifacts

Reviewers can refresh the checked-in dashboard demo output from the same safe local
fixture path with one command from the repo root:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py
```

Use this before a PR handoff when the FIFO engine, demo fixture, close-packet
writer, or dashboard fixture data changes. The command is deterministic for the
checked-in fixtures and should leave only intentional demo-output diffs.

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
- `close_packet.json` and `close_packet.md` with input checksums, safety mode, total COGS, failed SKU count, history status, and artifact list

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

## Local month-close packet

Every default JSON-producing `run` writes `close_packet.json` and
`close_packet.md` alongside the FIFO artifacts. The packet is a local audit
handoff containing input file names/checksums, generated timestamp, safety mode,
total COGS, processed SKUs, failed SKU count, optional month-history row, and the
artifact list. Use `--no-close-packet` only for explicit local/debug compatibility
checks; `--csv-only` also suppresses JSON/Markdown packet output.

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

## FIFO month-close management workflow summary

Use `workflow` after a local monthly run to see the corrected FirstLot management
lane in one read-only JSON payload: purchase-lot upload, sales upload, monthly COGS
run, SKU-level COGS table, failed-SKU queue, fix/rerun mode, append/reopen modes,
and rollback-plan visibility.

```bash
python3 -m app.local_cli workflow \
  --out /tmp/firstlot-demo \
  --period 2026-05 \
  --include-rollback-plan
```

The payload is intentionally boring and operational. It includes:

- `workflow_steps` for the real five-step FIFO close flow,
- `sku_level_cogs` rows with unit, shipping, total, and average cost fields derived from `cogs_detail`,
- `failed_sku_queue` rows for source CSV fixes,
- `month_history` for reopen/append audit context,
- `management_actions` with suggested local `failed-skus`, `fix-plan`, `--reopen`, `--append-prior-month`, and read-only rollback-plan commands,
- `live_mutations_performed: []` and prohibited-scope reminders.

It does not add demand planning, inventory planning, Amazon/Shopify connector UI,
mapping confidence panels, or product-planning workflow sections.

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
SKUs/periods, minimum additional available units needed, operator-facing summary
copy, recommended next action, `suggested_rerun_command`, and
`completion_check_command`. The command strings are guidance only; the command
does not edit CSVs, delete history, or touch live systems.

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

## PR-ready local handoff checklist

Before handing a local FirstLot demo branch to review, run the fixture-only checks
from the repo root:

```bash
python3 -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py -q
make check-firstlot-demo
```

If dashboard dependencies are installed, also run:

```bash
cd cogs-dashboard
npm test -- --runTestsByPath src/App.test.js --watchAll=false
```

The PR handoff doc for this checkpoint is
[`docs/plans/firstlot-local-month-close-pr-readiness.md`](plans/firstlot-local-month-close-pr-readiness.md).
It summarizes the safe workflow, regeneration commands, fixed-rerun flow,
`--assert-clear` gate, verification commands, and explicit out-of-scope items.

## Safety boundary

Use this CLI for synthetic fixtures and local/demo outputs only. Do not wire it to live Supabase or Storage Standard data without a separate reviewed adapter and explicit dry-run/commit split.
