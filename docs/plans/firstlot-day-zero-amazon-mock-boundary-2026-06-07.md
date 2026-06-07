# FirstLot day-0 + Amazon mock boundary — 2026-06-07

## Scope of this checkpoint

This branch continues the Sunday FirstLot lane with fixture/local-only product architecture for Amazon onboarding, inventory planning, and FIFO day-0 reconciliation.

Safety boundary remains unchanged:

- no `.env` reads or credential loading,
- no Seller Central OAuth,
- no Amazon SP-API / HTTP calls,
- no Supabase or production API writes,
- no Storage Standard/client data mutation,
- no real client CSVs.

## Draft FIFO day-0 rule

A proposed FirstLot FIFO day 0 is **not** simply the first month selected in the UI. The draft rule is:

> Use the earliest close-month start date where current Amazon inventory plus outside-warehouse stock can be reconciled back to source-backed purchase lots and freight. Every unmapped SKU, missing source document, unresolved freight allocation, or unapproved warehouse count remains an explicit blocker until an operator accepts or resolves it.

In the current mock fixture, `2026-05-01` is proposed but blocked/review-required because:

- `CAMERA-KIT` has 53 current units but only 47 source-backed units in draft support, plus partial freight.
- `TRIPOD` has enough draft source units but its outside-warehouse QA hold count needs supervisor sign-off.
- `STRAP-BUNDLE` has current and inbound inventory but no matched source units and missing freight allocation.
- `LENS-CAP-ONLY` exists in an outside warehouse count but is not mapped to the Amazon catalog / FirstLot SKU map.

## Mock Amazon connector contract

The current architecture is intentionally import-shaped but not live:

1. mock account metadata,
2. mock available Amazon SKU/inventory pull,
3. mock Amazon sales movements for the selected period,
4. mock prompt and fixture import for non-Amazon warehouse counts,
5. mock source-backed purchase-lot/freight guidance,
6. deterministic reconciliation payload,
7. blocked FIFO day-0 proposal.

The payload proves safety with:

- `connector_mode: mock`,
- `credentials_loaded: false`,
- `live_api_calls_performed: []`,
- `mutations_performed: []`.

## Live Amazon approval boundary

Live connector work should be a separate reviewed branch only after explicit approval. The first live phase should still be read-only/import-only:

- OAuth/auth wiring with no secrets committed or printed,
- SP-API report/order/inventory reads only,
- no listing edits,
- no FBA inventory changes,
- no order acknowledgements/cancellations/refunds,
- no DB writes until an explicit storage boundary is reviewed.

## Next build candidates

1. Turn the day-0 rule into a pure module with typed inputs and outputs instead of only orchestration logic.
2. Add fixture CSV import shape for outside-Amazon warehouse counts and source-backed freight/lots.
3. Add UI state for marking individual blockers as resolved in local page state only.
4. Add a generated day-0 review packet artifact beside the existing close packet.
5. Keep connector code split between contract/mock/read-only-live stubs so live work cannot accidentally leak into tests.
