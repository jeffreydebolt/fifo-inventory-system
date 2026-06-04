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

## Cycle 3 fixture/product additions

The PR branch now also previews three local-only assistant bricks:

1. **Upload mock queue** — fixture filenames, row counts, required-column coverage, and operator guidance. It intentionally does not expose real file pickers or storage writes.
2. **Export manifest gates** — packet file names, record counts, owners, and sign-off gates so accounting can see which artifacts are ready and which are blocked by exceptions.
3. **Replenishment action plan** — demand-planning recommendations converted into operator actions without Amazon/Shopify execution.

These remain static UI/documentation contracts until Jeff explicitly approves live connector or upload work.

## Cycle 4 final make-up polish

The final make-up cycle added three more safe/demo bricks without widening the live-data surface:

1. **Mapping confidence checklist** — expands mapping review from field cards into pass/review/deferred checks for FIFO keys, date parsing, landed-cost policy, and channel SKU aliases.
2. **Close readiness timeline** — visual operator timeline that separates ready intake, mapping review, generated FIFO artifacts, blocked exception sign-off, and draft accounting packet readiness.
3. **Accounting packet cover sheet** — export packet preview now includes prepared-for/prepared-by/open-blocker/regeneration-command rows before the artifact manifest.

These are fixture-backed UI states only. They do not enable real uploads, connector execution, API fetches, `.env` reads, live Supabase writes, or Storage Standard/client data mutation.
