# FirstLot local connector mocks

Cycle 2 adds a safe product-facing connector preview without touching live systems.

## Safety boundary

These mocks are documentation and checked-in UI state only:

- no Seller Central / Amazon SP-API calls,
- no Shopify calls,
- no Supabase writes,
- no Storage Standard/client data mutation,
- no `.env` reads,
- no credential-dependent code path.

## Amazon import-only mock contract

The demo UI presents three future import lanes that must remain local until reviewed:

| Lane | Local fixture contract | FirstLot destination | Autonomous guardrail |
| --- | --- | --- | --- |
| Orders / movements | `amazon_orders_fixture.csv` | normalized movement rows | read local CSV only; never require production tokens |
| SKU aliases | `amazon_sku_aliases_fixture.csv` | mapping review queue | stage aliases for operator approval; never write catalog data |
| Returns / adjustments | `amazon_returns_fixture.csv` | exception/adjustment review | show proposed close exceptions until reviewed |

## Product behavior expected later

1. User chooses a connector lane.
2. FirstLot shows a local/sample preview of detected columns and mapped fields.
3. Operator approves mappings before a FIFO run.
4. Connector imports are read-only until explicit production approval.
5. Export packets document the connector source used for the close.

## Current implementation

- UI data lives in `cogs-dashboard/src/workflowMocks.js`.
- UI rendering lives in `cogs-dashboard/src/pages/DemoPage.js`.
- Dashboard tests assert connector mocks render and make no network calls.
