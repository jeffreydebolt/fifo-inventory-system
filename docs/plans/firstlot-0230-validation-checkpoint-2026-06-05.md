# FirstLot 02:30 client-test validation checkpoint — 2026-06-05

## Safety boundary

Work stayed local/fixture-only. No `.env`/secret reads, no Supabase/API imports, no live database writes, no Storage Standard/client data, and no deploy.

## Branch

`autonomous/firstlot-client-test-validation-2026-06-05`

## Completed in this block

- Added a dependency-free local CSV validator at `core/csv_validation.py`.
- Added `python3 -m app.local_cli validate --lots ... --movement ...`.
- Made `app.local_cli run` validate by default and stop before artifact writes if validation fails.
- Added explicit `--skip-validation` as a local/debug override only.
- Added synthetic bad CSV fixtures under `tests/fixtures/firstlot_validation/`.
- Added tests for good validation, bad validation, CLI JSON output, and failed-run write blocking.
- Documented the validation command and safety behavior in `docs/local-demo-cli.md`.

## Validation checks covered

- Required purchase-lot columns.
- Required movement/sales columns.
- ISO date/datetime parsing.
- Integer quantities.
- Nonnegative unit cost and freight.
- Positive original lot quantities.
- Nonnegative and not-over-original remaining quantities.
- Positive sale quantities for client-test close runs.
- Duplicate lot IDs.
- Duplicate sale IDs.

## Commands run

```bash
python3 -m pytest tests/unit/test_csv_validation.py tests/unit/test_local_csv_cli.py tests/unit/test_firstlot_demo_outputs.py tests/unit/test_failed_sku_workflow.py -q
```

Result: `20 passed in 0.56s`.

```bash
make check-firstlot-demo
```

Result: passed. It regenerated safe fixture artifacts, verified 12 artifacts, and ran dashboard Jest smoke with `3 passed`. Non-blocking warnings remained: React Router future flags and Node `punycode` deprecation.

```bash
python3 -m app.local_cli validate --lots tests/fixtures/firstlot_demo/purchase_lots.csv --movement tests/fixtures/firstlot_demo/movement.csv
```

Result: JSON with `"valid": true`.

```bash
python3 -m app.local_cli validate --lots tests/fixtures/firstlot_validation/bad_purchase_lots.csv --movement tests/fixtures/firstlot_validation/bad_movement.csv
```

Result: expected exit code `1`; JSON included deterministic operator errors.

```bash
python3 -m pytest tests/unit -q
```

Result: blocked in the base environment because `pandas` is not installed for two legacy unit modules.

```bash
uv run --with pandas python -m pytest tests/unit -q
```

Result: `30 passed, 1 skipped in 6.78s`.

## Remaining continuation queue

1. Add month-close `close_packet.json` / `close_packet.md` generated from local runs.
2. Add synthetic second-client-style fixture templates and mapping docs without using client data.
3. Optionally surface validation state in the demo UI using checked-in fixture data only.
