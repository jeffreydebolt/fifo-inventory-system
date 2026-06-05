# FirstLot local close packet

- Safety mode: `local_fixture_only_no_live_writes`
- Period: `2026-05`
- Generated at: `2026-06-03T23:00:00`
- SKUs processed: 2 (SKU-A, SKU-B)
- Total units sold: 21
- Total COGS: 263.00
- Failed SKU count: 0
- Shortfall quantity: 0
- Operator next step: Review close packet and retain artifacts for local audit handoff.

## Input files

- Purchase lots: `tests/fixtures/firstlot_demo/purchase_lots_fixed.csv` sha256 `e43ed38b8e90929219243bbb04a2811222abab8082bf5c734b8f03bf590ab356`
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
- `month_history.csv`
- `month_history.json`

## Safety

No live database writes, no Supabase/API imports, no `.env` reads, and no Storage Standard/client-data mutation are part of this packet.
