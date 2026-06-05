# FirstLot close-packet checkpoint — 2026-06-05

## Safety boundary

Work stayed synthetic/local only: no `.env`, no Supabase/API imports, no live database writes, no Storage Standard/client data, and no deploy.

## Branch

`autonomous/firstlot-close-packet-2026-06-05`

## Completed

- Added `core/close_packet.py` to write `close_packet.json` and `close_packet.md` for local FirstLot FIFO runs.
- Close packets include:
  - safety mode,
  - generated timestamp,
  - period(s),
  - input file names and SHA-256 checksums,
  - processed SKUs,
  - total units sold,
  - total COGS,
  - failed SKU count/shortfall quantity,
  - optional month-history row,
  - artifact list,
  - operator next step.
- `app.local_cli run` now writes packets by default for JSON-producing runs.
- Added `--no-close-packet` for explicit local/debug compatibility; `--csv-only` also suppresses packet output.
- Regenerated checked-in synthetic demo artifacts so v1 and v2 demo output folders include close packets.
- Updated docs and tests.

## Verification

```bash
python3 -m pytest tests/unit/test_close_packet.py tests/unit/test_csv_validation.py tests/unit/test_local_csv_cli.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py -q
```

Result: `22 passed in 0.65s`.

```bash
make check-firstlot-demo
```

Result: passed. It regenerated 14 temp artifacts including `close_packet.json/md` and ran dashboard Jest smoke with `3 passed`. Non-blocking warnings remained: React Router future flags and Node `punycode` deprecation.

```bash
uv run --with pandas python -m pytest tests/unit -q
```

Result: `32 passed, 1 skipped in 1.11s`.

## Remaining queue

1. Add synthetic second-client CSV template/mapping docs.
2. Optionally show close-packet summary in fixture-only demo UI.
3. Continue keeping live connectors/API production workflow out of scope until explicitly approved.
