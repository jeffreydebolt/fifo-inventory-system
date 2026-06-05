# FirstLot local month-close PR readiness handoff

This handoff describes the current PR checkpoint for the safe, fixture-backed FirstLot local month-close workflow. It is intentionally local/demo only: no `.env`, no Supabase, no Storage Standard client data, no production deploy, and no live database writes.

## Current branch checkpoint

- Branch: `autonomous/fifo-nightly-2026-06-04-early`
- Intended PR theme: complete the local FirstLot fix/rerun demo workflow.
- Reviewer entry points:
  - CLI/docs: `docs/local-demo-cli.md`
  - Demo UI: `cogs-dashboard/src/pages/DemoPage.js`
  - Regeneration script: `scripts/regenerate_firstlot_demo_artifacts.py`
  - Fixture inputs: `tests/fixtures/firstlot_demo/`
  - Checked-in demo output:
    - v1 failed run: `cogs-dashboard/src/demo-output/firstlot_demo/`
    - v2 fixed rerun: `cogs-dashboard/src/demo-output/firstlot_demo_fixed/`

## Safe local workflow now supported

The local path demonstrates the intended FirstLot operator loop without touching live systems:

1. Select fixture purchase lots CSV and sales/movement CSV.
2. Run FIFO COGS for a period.
3. Review SKU-level COGS detail, remaining layers, audit rows, shortfalls, and failed-SKU queue.
4. Generate a read-only failed-SKU fix plan.
5. Correct local fixture input (represented by `purchase_lots_fixed.csv`).
6. Rerun the period with `--reopen`.
7. Assert the failed-SKU queue is clear.
8. Preserve local month history showing the v1 needs-fix run and v2 reopened/fixed run.
9. Produce a read-only rollback plan if needed; no rollback mutation is executed.

## Regenerate checked-in demo artifacts

From the repo root:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py
```

This refreshes both checked-in fixture output folders by default:

- `cogs-dashboard/src/demo-output/firstlot_demo/` for the v1 fixture run with a queued SKU-A shortfall.
- `cogs-dashboard/src/demo-output/firstlot_demo_fixed/` for the v1+v2 fixed-rerun packet using `purchase_lots_fixed.csv`.

For temporary reviewer output instead of checked-in folders:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py \
  --out /tmp/firstlot-demo-v1 \
  --fixed-out /tmp/firstlot-demo-fixed
```

## Run the fixed-rerun flow manually

Start with the intentionally short v1 run:

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

Review the failed SKU queue:

```bash
python3 -m app.local_cli failed-skus \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05
```

Generate the read-only fix plan:

```bash
python3 -m app.local_cli fix-plan \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05 \
  --lots tests/fixtures/firstlot_demo/purchase_lots.csv \
  --movement tests/fixtures/firstlot_demo/movement.csv \
  --note "add missing local lot and rerun"
```

Expected safety fields in the fix plan:

- `read_only: true`
- `mutations_performed: []`
- `affected_skus` / affected period metadata
- minimum additional units required
- suggested rerun arguments

Rerun the period with corrected fixture input:

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

Assert the queue clears:

```bash
python3 -m app.local_cli failed-skus \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05 \
  --assert-clear
```

Expected clear result:

```json
{
  "clear": true,
  "queue_record_count": 0,
  "queue_records": [],
  "total_shortfall_quantity": 0
}
```

The `--assert-clear` command exits non-zero if matching failed-SKU rows remain, so it can be used as a local PR/reviewer gate.

## Read-only history and rollback-plan checks

Print local month history:

```bash
python3 -m app.local_cli history --out /tmp/firstlot-demo-rerun
```

Print a read-only rollback plan:

```bash
python3 -m app.local_cli rollback-plan \
  --out /tmp/firstlot-demo-rerun \
  --period 2026-05 \
  --generated-at 2026-06-03T23:00:00 \
  --note "review rollback packet only"
```

The rollback plan is documentation/audit output only. It must not execute delete, restore, rollback, Supabase, or live-data mutation scripts.

## PR verification commands

Run these from the repo root before handing the branch to review:

```bash
python3 -m pytest tests/unit/test_local_csv_cli.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py -q
make check-firstlot-demo
```

If dashboard dependencies are available, also run:

```bash
cd cogs-dashboard
npm test -- --runTestsByPath src/App.test.js --watchAll=false
```

## Out of scope for this PR checkpoint

These remain explicitly out of scope:

- Live database writes or migrations.
- Reading `.env` or printing secrets.
- Supabase/API-backed workflow.
- Source connectors for Shopify, Amazon, Google Sheets, Storage Standard, or other production systems.
- Mutating Storage Standard client files/data.
- Production deploys.
- Pushing/opening a PR without Jeff approval.
- Automatic rollback mutation. Current rollback behavior is read-only plan output only.
- CSV validation feature work beyond existing fixture/test coverage.
- Local API wrapper or live adapter implementation.

## Risk notes / remaining build queue

- This is PR-ready as a local/demo checkpoint if the verification commands pass in the reviewer environment.
- The checked-in UI displays fixture artifacts; it does not yet accept arbitrary local uploads in-browser.
- Next planned build phase: add local CSV validation before FIFO run, with bad-fixture tests and no live integrations.
