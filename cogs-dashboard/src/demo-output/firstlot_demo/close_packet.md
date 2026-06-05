# FirstLot local close packet

- Safety mode: `local_fixture_only_no_live_writes`
- Period: `2026-05`
- Generated at: `2026-06-03T23:00:00`
- SKUs processed: 2 (SKU-A, SKU-B)
- Total units sold: 20
- Total COGS: 250.00
- Failed SKU count: 1
- Shortfall quantity: 1
- Operator next step: Fix local input CSVs and rerun with --reopen, then assert failed-skus --assert-clear.

## Input files

- Purchase lots: `tests/fixtures/firstlot_demo/purchase_lots.csv` sha256 `78f980fbe1a8a799af5803c27a962a0bc10e4470df2d0a86aa961a909d4894a6`
- Movement: `tests/fixtures/firstlot_demo/movement.csv` sha256 `9eb3c62bda9c90dc1dcbf50f71363fb94388d81d3da671f7dd200596607411ff`

## Artifacts

- `cogs_summary.csv`
- `cogs_summary.json`
- `remaining_layers.csv`
- `remaining_layers.json`
- `audit_trail.csv`
- `audit_trail.json`
- `shortfalls.csv`
- `shortfalls.json`
- `failed_sku_queue.csv`
- `failed_sku_queue.json`
- `cogs_detail.csv`
- `cogs_detail.json`

## Safety

No live database writes, no Supabase/API imports, no `.env` reads, and no Storage Standard/client-data mutation are part of this packet.
