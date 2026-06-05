# FirstLot weekend client CSV test packet

Use this packet to test FirstLot against another client's CSV exports safely. This path is **local-only**: it validates two CSV files, runs deterministic FIFO month-close output into a temp folder, and prints a review summary. It must not read `.env`, import Supabase/API adapters, mutate live data, mutate Storage Standard/client data, or deploy anything.

## 0. Safety rules for the weekend test

Do:

- Work from this public repo checkout only.
- Use a temporary output folder under `/tmp` or `/private/tmp`.
- Use copies of CSV exports, never source-of-truth files.
- Rename/copy inputs into a local fixture folder with exactly these names:
  - `purchase_lots.csv`
  - `movement.csv`
- Keep any real client CSV folder outside git, or use an ignored scratch folder such as `local-client-fixtures/<client-slug>/`.
- Review generated artifacts before sharing them.

Do **not**:

- Read, source, copy, or print `.env` files or secrets.
- Run upload/delete/rollback/restore/migrate/clean/fix live-data scripts.
- Write to Supabase, Storage Standard, accounting systems, ecommerce systems, or production APIs.
- Commit real client CSVs or generated client-specific artifacts.
- Use `--clean-output` on anything outside the system temp directory; the wrapper blocks this by design.

Before committing any repo changes made during test prep, run:

```bash
make check-no-client-data-commit
```

## 1. Required CSV shapes

### `purchase_lots.csv`

Required header:

```csv
lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit
```

Field expectations:

| Field | Meaning | Validation expectation |
| --- | --- | --- |
| `lot_id` | Unique purchase lot identifier | Required, no duplicates |
| `sku` | Product SKU matching sales rows | Required |
| `received_date` | Date inventory became available | ISO date, e.g. `2026-06-01` |
| `original_quantity` | Original purchased units | Integer, nonnegative |
| `remaining_quantity` | Units available for this close | Integer, nonnegative |
| `unit_price` | Merchandise unit cost | Numeric, nonnegative |
| `freight_cost_per_unit` | Shipping/freight unit cost | Numeric, nonnegative |

### `movement.csv`

Required header:

```csv
sale_id,sku,sale_date,quantity_sold
```

Field expectations:

| Field | Meaning | Validation expectation |
| --- | --- | --- |
| `sale_id` | Unique sale/order line identifier | Required, no duplicates |
| `sku` | Product SKU matching purchase lots | Required |
| `sale_date` | Sale date in close month | ISO date, e.g. `2026-06-12` |
| `quantity_sold` | Units sold | Integer greater than zero |

## 2. Preflight with the synthetic second-client fixture

From repo root, confirm the safe workflow still works before using another client's files:

```bash
make check-firstlot-weekend

python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir tests/fixtures/firstlot_second_synthetic_client \
  --out /tmp/firstlot-second-synthetic-client \
  --period 2026-06 \
  --expect-clear \
  --clean-output
```

Expected synthetic high-level result:

- validation `valid: true`,
- failed-SKU queue `clear: true`,
- total COGS `723.00`,
- remaining inventory value `485.50`,
- no live writes or secret reads.

## 3. Prepare another client's CSVs without committing them

Create an ignored local scratch folder and copy sanitized exports into it:

```bash
mkdir -p local-client-fixtures/weekend-client-a
cp /path/to/exported-purchase-lots.csv local-client-fixtures/weekend-client-a/purchase_lots.csv
cp /path/to/exported-sales.csv local-client-fixtures/weekend-client-a/movement.csv
```

Confirm the files are not staged:

```bash
git status --short local-client-fixtures/weekend-client-a
```

If git shows real client files as staged or tracked, stop and unstage/remove them from the repo workflow before continuing.

## 4. Normalize client-shaped CSV exports when needed

Some real exports will be close to the FirstLot shape but not exact. For example, lot exports may use `po_number`, `original_unit_qty`, `remaining_unit_qty`, `$` currency values, comma quantities, M/D/YY dates, and trailing blank columns. Sales exports may use `SKU`, `Quantity_Sold`, `Sale_Month_Str`, and omit sale IDs.

Inspect the inputs first:

```bash
python3 -m app.local_cli inspect-lots \
  --lots local-client-fixtures/weekend-client-a/lots_export.csv

python3 -m app.local_cli inspect-movement \
  --movement local-client-fixtures/weekend-client-a/sales_export.csv
```

Normalize into the strict file names used by the FIFO runner:

```bash
python3 -m app.local_cli normalize-lots \
  --lots local-client-fixtures/weekend-client-a/lots_export.csv \
  --out local-client-fixtures/weekend-client-a/purchase_lots.csv

python3 -m app.local_cli normalize-movement \
  --movement local-client-fixtures/weekend-client-a/sales_export.csv \
  --out local-client-fixtures/weekend-client-a/movement.csv
```

Normalization is local-file only. It does not read `.env`, import Supabase/API adapters, call production systems, or mutate live/client data. When the sales export lacks `sale_id`, FirstLot generates deterministic local IDs like `SALE-0001` for the test run.

## 5. Validate only — no FIFO artifacts written

Run validation first:

```bash
python3 -m app.local_cli validate \
  --lots local-client-fixtures/weekend-client-a/purchase_lots.csv \
  --movement local-client-fixtures/weekend-client-a/movement.csv
```

Proceed only when the JSON response includes:

```json
{
  "valid": true,
  "errors": []
}
```

If validation fails, fix the local CSV copy and rerun validation. Do not use `--skip-validation` for weekend client testing.

## 6. Run the local month-close packet

Choose the month being tested, then run into `/tmp`:

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir local-client-fixtures/weekend-client-a \
  --out /tmp/firstlot-weekend-client-a-2026-06 \
  --period 2026-06 \
  --clean-output
```

Add `--expect-clear` only when the test should fail unless all sales can be fully matched to purchase lots:

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir local-client-fixtures/weekend-client-a \
  --out /tmp/firstlot-weekend-client-a-2026-06 \
  --period 2026-06 \
  --expect-clear \
  --clean-output
```

The wrapper prints a JSON summary with:

- `read_only_local_fixture_workflow: true`,
- `mutations_performed: []`,
- validation result,
- failed-SKU queue summary,
- artifact count,
- total COGS,
- remaining inventory value,
- processed SKUs,
- safety statement.

## 7. Review generated artifacts

Open the temp output folder only; do not move generated real-client artifacts into git:

```bash
open /tmp/firstlot-weekend-client-a-2026-06
```

Review these files:

| Artifact | What to check |
| --- | --- |
| `close_packet.md` | Executive close summary, safety mode, input checksums, artifact list |
| `close_packet.json` | Machine-readable packet for exact totals and failed count |
| `cogs_summary.csv/json` | Total COGS by SKU/month |
| `cogs_detail.csv/json` | Units sold, merchandise/unit cost, shipping, total COGS, average COGS, status |
| `remaining_layers.csv/json` | Unsold remaining purchase layers |
| `audit_trail.csv/json` | Sale-to-lot FIFO allocation trail |
| `failed_sku_queue.csv/json` | SKUs where sales exceeded available purchase lots |
| `shortfalls.csv/json` | Sale-level partial/unmatched quantities |
| `month_history.csv/json` | Local output-folder history row for the period |

## 8. Interpret failed SKUs safely

If failed SKUs remain, generate a read-only operator plan:

```bash
python3 -m app.local_cli fix-plan \
  --out /tmp/firstlot-weekend-client-a-2026-06 \
  --period 2026-06 \
  --lots local-client-fixtures/weekend-client-a/purchase_lots.csv \
  --movement local-client-fixtures/weekend-client-a/movement.csv \
  --note "weekend test local fix plan"
```

The plan must include:

- `read_only: true`,
- `mutations_performed: []`,
- affected SKUs/periods,
- minimum additional units needed,
- suggested rerun and completion-check commands.

Fix only the local CSV copy, then rerun the same output folder with `--reopen`:

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir local-client-fixtures/weekend-client-a \
  --out /tmp/firstlot-weekend-client-a-2026-06 \
  --period 2026-06 \
  --reopen
```

Finally assert the queue is clear when expected:

```bash
python3 -m app.local_cli failed-skus \
  --out /tmp/firstlot-weekend-client-a-2026-06 \
  --period 2026-06 \
  --assert-clear
```

## 9. Weekend result note template

Use this short template for the 06:05 report or PR/test notes:

```markdown
## FirstLot weekend client CSV smoke

- Client/test label: <sanitized label only>
- Period: <YYYY-MM>
- Input location: local scratch only, not committed
- Command: `python3 scripts/run_firstlot_client_fixture.py ...`
- Validation: pass/fail
- Failed SKU queue: clear/not clear; count <n>; total shortfall <n>
- Total COGS: <amount>
- Remaining inventory value: <amount>
- Artifacts reviewed: close_packet, cogs_detail, remaining_layers, audit_trail, failed_sku_queue
- Safety: no .env, no Supabase/API imports, no live DB writes, no deploy, no client artifacts committed
- Follow-up: <CSV cleanup / SKU mapping / lot availability / ready for reviewer>
```

## 10. Stop conditions

Stop and report instead of continuing if:

- CSV prep requires secrets, `.env`, Storage Standard, or production API access.
- The only available data lives in source-of-truth client folders and cannot be copied safely.
- Validation errors suggest the export schema is materially different from this packet.
- Any command would mutate live/client data or deploy.
- `git status` shows real client CSVs or generated real-client artifacts staged for commit.
