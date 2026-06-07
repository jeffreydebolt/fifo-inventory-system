# FirstLot 06:05 report notes — 2026-06-07

## Scope completed

- Recovered from the stale `autonomous/fifo-nightly-2026-06-04-early` branch by inspecting it, confirming its local commits, then continuing from current `main` on `autonomous/firstlot-weekend-csv-2026-06-07` so the already-merged weekend/client CSV work was not regressed.
- Added a human-readable `client_smoke_summary.md` artifact beside `client_smoke_summary.json` for another-client CSV smoke runs.
- The markdown summary includes pass/fix status, period, validation status, total COGS, failed SKU count, shortfall quantity, normalized input paths, safety line, mutations performed, and the next operator command.
- Failed-SKU smoke runs now also surface missing-lot repair files and recommended CSV fixes in markdown without inventing source data.

## Safety

- Fixture/local-only work.
- No `.env` reads.
- No Supabase/API imports added.
- No live database writes.
- No Storage Standard/client data touched.
- No deploy.
- Real client CSVs remain excluded by `local-client-fixtures/` and `*.csv` ignore rules, except tracked tiny fixtures.

## Verification to report

Run these before final handoff/merge:

```bash
python3 -m pytest tests/unit/test_client_smoke_runner.py -q
make check-firstlot-weekend
cd cogs-dashboard && npm test -- --runTestsByPath src/App.test.js --watchAll=false
python3 -m app.local_cli client-smoke \
  --lots tests/fixtures/firstlot_client_exports/sample_lots_client_shape.csv \
  --movement tests/fixtures/firstlot_client_exports/sample_sales_client_shape.csv \
  --out /tmp/firstlot-client-smoke-md-check \
  --period 2025-09 \
  --json-out /tmp/firstlot-client-smoke-md-check-summary.json \
  --clean-output
```

## Review notes

- This is a small PR-sized checkpoint that improves weekend testability for another client's CSVs: Jeff can open the temp output folder and read `client_smoke_summary.md` before drilling into JSON/CSV artifacts.
- Remaining queue: run against a real copied client export outside git, then tune normalizer aliases only if a new export header shape appears.
