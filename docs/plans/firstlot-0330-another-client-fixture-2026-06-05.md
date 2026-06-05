# FirstLot 03:30 another-client fixture builder — 2026-06-05

Safety boundary honored: local fixture/test work only. No `.env` or secrets read, no Supabase/API imports added, no live database writes, no Storage Standard/client data mutation, and no deploy.

## Branch

`autonomous/firstlot-another-client-fixture-2026-06-05`

## What changed

- Added a second synthetic client-style fixture under `tests/fixtures/firstlot_second_synthetic_client/`:
  - `purchase_lots.csv`
  - `movement.csv`
  - fixture README with expected safe command and expected totals.
- Added `scripts/run_firstlot_client_fixture.py`, a generic local wrapper that:
  - validates a fixture directory containing `purchase_lots.csv` and `movement.csv`,
  - runs the existing local FIFO CLI into a local output folder,
  - writes close-packet/month-history artifacts through the existing safe local CLI,
  - optionally asserts the failed-SKU queue is clear,
  - can clean temp output directories only.
- Expanded `docs/local-demo-cli.md` with the generic weekend client-test workflow and copy/paste commands.
- Added tests proving the second synthetic fixture validates and the generic workflow returns the expected local close summary.

## Synthetic fixture expected result

Command:

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir tests/fixtures/firstlot_second_synthetic_client \
  --out /tmp/firstlot-second-synthetic-client \
  --period 2026-06 \
  --expect-clear \
  --clean-output
```

Expected result:

- validation passes,
- failed-SKU queue clear,
- total COGS `723.00`,
- remaining inventory value `485.50`,
- processed SKUs: `CAMERA-KIT`, `STRAP-BUNDLE`, `TRIPOD`.

## Verification to run/report

- `python3 -m pytest tests/unit/test_csv_validation.py -q`
- broader local FirstLot suite/check after commit.

## Remaining risk

Low and bounded: fixture/local-only. The generic wrapper shells out to the existing local CLI and only cleans output folders under the system temp directory when `--clean-output` is provided.
