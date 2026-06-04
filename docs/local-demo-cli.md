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

## Regenerate dashboard demo artifacts

Reviewers can refresh the checked-in dashboard demo output from the same safe local
fixture path with one command from the repo root:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py
```

That command rewrites `cogs-dashboard/src/demo-output/firstlot_demo/*.csv` and
`*.json`, then verifies the expected files exist and the JSON parses. It is still
local-file only: fixture CSV input, deterministic timestamp, no `.env`, no
Supabase/API imports, and no live database writes.

Expected artifacts:

- `cogs_summary.csv` and `cogs_summary.json`
- `remaining_layers.csv` and `remaining_layers.json`
- `audit_trail.csv` and `audit_trail.json`
- `shortfalls.csv` and `shortfalls.json`

The fixture demonstrates:

- multi-lot FIFO consumption for `SKU-A`,
- remaining layer output for `SKU-B`,
- sale-to-lot audit rows,
- an explicit partial shortfall for `SALE-002`,
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

## Safety boundary

Use this CLI for synthetic fixtures and local/demo outputs only. Do not wire it to live Supabase or Storage Standard data without a separate reviewed adapter and explicit dry-run/commit split.
