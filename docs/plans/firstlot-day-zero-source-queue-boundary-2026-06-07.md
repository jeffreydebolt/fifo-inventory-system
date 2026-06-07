# FirstLot Day-Zero Source Queue + Live Connector Boundary — 2026-06-07

Branch: `autonomous/firstlot-sunday-ui-amazon-mock`

## Scope

This continuation deepens the mock/local Amazon onboarding lane without adding live connectors, credentials, database writes, or client data.

The product direction remains:

1. Connect Amazon in a future approved path.
2. Pull available inventory/SKUs and sales movements.
3. Ask for non-Amazon warehouses and upload outside-Amazon SKU/counts.
4. Upload purchase lots and freight evidence.
5. Try to roll inventory backward from current stock/sales/receipts.
6. Propose a FIFO day 0 only when blockers are visible and operator-approved.

## Day 0 rule draft

A FIFO day-zero proposal should start as the requested close month start, then remain blocked unless all of these are true:

- Amazon sales/order/report history covers the rollback window.
- Current Amazon units plus outside-warehouse units are reconciled.
- Every outside-only SKU has an explicit map/archive/exclude decision.
- Current units are source-backed to purchase lots.
- Freight allocations are attached or explicitly marked not required.
- Any estimated negative rollback position is explained by receipt timing, missing sales, or an operator-approved exception.
- An operator explicitly approves the day-zero layers before accounting reliance.

## New deterministic mock payload shape

`core.amazon_onboarding.build_amazon_onboarding_mock()` now exposes additional fixture-only fields:

- `warehouse_reconciliation_summary`: per-SKU Amazon units, reserved units, outside-warehouse units, cover days, lead time, and stockout risk.
- `source_document_queue`: present/missing source evidence and operator guidance for each SKU, including warehouse-only SKUs.
- `current_in_stock_vs_lot_matching[].day_zero_layer_candidate`: draft units/cost/freight/value that may become a day-zero layer only after blockers are resolved.
- `proposed_fifo_day_0.start_date_candidate_basis`: the rule notes shown in UI.
- `proposed_fifo_day_0.approval_boundary`: reminder that the mock proposal is not accounting-ready.
- `live_connector_approval_boundary`: machine-readable safety line between allowed mock work and explicitly forbidden live connector work.

## Live Amazon approval boundary

Allowed now:

- local fixture reads
- mock connector payload generation
- deterministic tests
- static UI demo

Explicitly not allowed without Jeff approval:

- Amazon OAuth
- Seller Central/SP-API HTTP calls
- credential loading
- Supabase/live DB writes
- Storage Standard/client data mutation
- production persistence or mutation paths

## UI copy goal

The `/demo` page should feel like a command-center product surface, not a raw demo:

- clear Amazon onboarding timeline
- connector approval boundary card
- inventory reconciliation table
- day-zero rule basis
- readiness gates
- rollback reconstruction
- blocker table
- source document queue
- planning/replenishment table

The copy still states that everything is local/demo/fixture-only and not wired to live Amazon, uploads, Supabase, or client data.

## Next risk boundary

The next meaningful risk boundary is live connector design. That should be a separate reviewed branch only after explicit approval, starting read-only and credential-safe. Until then, keep connector work fixture-backed and deterministic.
