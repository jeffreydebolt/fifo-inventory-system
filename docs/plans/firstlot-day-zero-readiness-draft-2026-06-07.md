# FirstLot FIFO Day 0 Readiness Draft — 2026-06-07

Branch: `autonomous/firstlot-sunday-ui-amazon-mock`

## Scope

This is a local/mock-first product draft for the onboarding path:

1. connect Amazon in mock mode,
2. pull available SKUs/in-stock counts from fixture data,
3. ask about non-Amazon warehouses,
4. ingest outside-Amazon SKU/count fixtures,
5. ingest source-backed purchase lot/freight guidance fixtures,
6. attempt a backward inventory reconstruction, and
7. propose FIFO day 0 with blockers.

No live Amazon SP-API, Seller Central, Supabase, production API, Storage Standard, or credential path is implemented here.

## Draft day 0 rule

Propose FIFO day 0 as the earliest close-month start where current Amazon plus outside-warehouse stock can be reconciled to source-backed purchase lots/freight, while every unresolved exception remains visible as a blocker.

The current mock payload includes these readiness gates:

- Amazon sales history covers the rollback window.
- Every current SKU is mapped to Amazon or explicitly handled as an outside-warehouse decision.
- Purchase lots source-back all current units.
- Freight allocations are attached or explicitly not required.
- Operator approves the proposed FIFO day 0.

## Backward reconstruction draft

For each Amazon SKU, the mock computes:

```text
estimated_units_at_period_start = current_units + period_sales_units - draft_receipts_in_period
```

This is intentionally a first-pass operator planning estimate, not an accounting result. It can only become a trusted start layer after confirming:

- Amazon sales history completeness,
- inbound receipt timing,
- purchase lot source documents,
- freight allocation support,
- outside-warehouse count status, and
- SKU mapping/archival decisions for warehouse-only SKUs.

Negative estimated start units are automatically blocked because receipts appear to exceed current stock plus sales in the mock rollback window.

## Live Amazon approval boundary

Future live Amazon work must be a separate reviewed branch and requires Jeff's explicit approval before any credential, OAuth, HTTP client, Seller Central, or SP-API behavior is added. Until then, Amazon-related objects must keep safety proof fields:

- `connector_mode: mock`
- `credentials_loaded: false`
- `live_api_calls_performed: []`
- `mutations_performed: []`

## Next product risk boundary

The next risky design decision is how strict FirstLot should be before accepting day 0:

- accept only fully source-backed, freight-backed SKUs, or
- allow a blocked/provisional start layer with unresolved SKUs excluded from COGS until fixed.

The current implementation chooses the safer posture: proposal allowed, accounting reliance blocked until operator confirmation and source support are complete.
