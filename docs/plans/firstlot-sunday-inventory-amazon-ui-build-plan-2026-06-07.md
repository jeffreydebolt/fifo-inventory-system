# FirstLot Sunday Inventory + Amazon Mock + Polished UI Build Plan

> **For Hermes:** Use subagent-driven-development style execution, but keep this repo’s AGENTS.md safety rules above all else.

**Goal:** Move FirstLot from a safe FIFO COGS demo into a more polished inventory command center that also previews inventory tracking, replenishment planning, Amazon onboarding, and FIFO day-zero reconstruction.

**Architecture:** Keep all new work local/mock-first. Build the product shell and deterministic contracts now; defer live Amazon SP-API OAuth/API calls until Jeff explicitly approves credentials/live connector work. The core differentiated layer remains FirstLot-owned: source-backed lots/freight, current inventory snapshots, sales movement imports, rollback-to-day-zero reasoning, FIFO COGS, run versions, failed SKU queue, and planning views.

**Tech Stack:** Python 3.11 local core/CLI/tests; React dashboard demo under `cogs-dashboard`; local JSON/CSV fixtures; no Supabase/live DB writes; no `.env`; no live Amazon calls.

---

## Product direction decision

Do **not** clone/fork a full ERP as the production base.

Use references:

- ERPNext (`frappe/erpnext`) for stock ledger, FIFO valuation, stock reconciliation, landed cost/freight concepts.
- InvenTree (`inventree/InvenTree`) for inventory UX/API patterns and item/location workflows; possible experimental fork only, not production base.
- Odoo (`odoo/odoo`) for polished ERP inventory UX patterns.
- Amazon SP-API references/libraries for future connector implementation:
  - `saleweaver/python-amazon-sp-api`
  - `amzn/selling-partner-api-samples`

Build FirstLot’s own focused domain layer because the unique workflow is not generic ERP: Amazon login → pull available inventory/SKUs and sales → ask about non-Amazon warehouses → upload SKU/counts → upload purchase lots/freight → reconcile current in-stock → roll backward as far as possible → determine FIFO day 0/start date → run FIFO COGS and planning.

---

## Hard safety boundaries

Allowed today:

- local branch work
- deterministic fixtures
- local React demo UI
- Python core contracts/tests
- local CLI commands
- docs/checkpoint files
- local commits after tests pass

Forbidden today unless Jeff explicitly approves:

- `.env` reads/sourcing/printing
- live Amazon SP-API calls
- live Supabase/API/database writes
- Storage Standard/client data mutation
- real client CSV commits
- production deploys
- main-branch pushes
- upload/delete/rollback/restore/migrate/clean/fix live-data scripts

Every new Amazon-related payload must include safety proof fields:

- `connector_mode: "mock"`
- `credentials_loaded: false`
- `live_api_calls_performed: []`
- `mutations_performed: []`

---

## Build queue

### Slice 1 — Branch and plan

- Branch: `autonomous/firstlot-sunday-ui-amazon-mock`
- Add this plan under `docs/plans/`.
- Decide what to do with the existing overnight checkpoint doc before final verification.

Verification:

```bash
git status --short --branch
```

### Slice 2 — Operator-quality validation guidance

Goal: make CSV validation errors read like product/operator guidance instead of raw codes.

Files likely modified:

- `core/csv_validation.py`
- `app/local_cli.py`
- `core/client_smoke.py`
- `tests/unit/test_csv_validation.py`
- `tests/unit/test_local_csv_cli.py`
- `tests/unit/test_client_smoke_runner.py`

Expected improvements:

- preserve existing issue fields but add display metadata when practical:
  - `severity`
  - `title`
  - `details`
  - `suggested_action`
  - `blocking`
- add or improve cross-file checks where safe:
  - movement SKU not present in purchase lots
  - sale date before first received lot for SKU
- add `validate --human` output if feasible.
- include top validation issues/next action in `client_smoke_summary.md`.

Verification:

```bash
python3 -m pytest tests/unit/test_csv_validation.py tests/unit/test_local_csv_cli.py tests/unit/test_client_smoke_runner.py -q
```

Commit target:

```bash
git commit -m "feat: add operator validation guidance"
```

### Slice 3 — Amazon SP-API mock onboarding architecture

Goal: prove the onboarding/sync shape without credentials or live calls.

Files to add/modify:

- `core/connectors/__init__.py`
- `core/connectors/amazon_sp_api_contract.py`
- `core/connectors/amazon_sp_api_mock.py`
- `core/amazon_onboarding.py`
- `app/local_cli.py`
- `tests/fixtures/amazon_sp_api_mock/*`
- `tests/unit/test_amazon_sp_api_mock_connector.py`
- `tests/unit/test_amazon_onboarding.py`
- `tests/unit/test_local_cli_amazon_onboarding.py`

CLI target:

```bash
python3 -m app.local_cli amazon-onboarding-mock \
  --fixture-dir tests/fixtures/amazon_sp_api_mock \
  --period 2026-05
```

Payload must show:

- mock Amazon connection/account
- available SKUs/inventory
- recent sales movements
- other warehouse prompt/count fixture support
- source-backed purchase lots/freight guidance
- current in-stock vs lot matching
- proposed FIFO day 0 requiring operator confirmation
- no credentials/live calls/mutations

Verification:

```bash
python3 -m pytest tests/unit/test_amazon_sp_api_mock_connector.py tests/unit/test_amazon_onboarding.py tests/unit/test_local_cli_amazon_onboarding.py -q
```

Commit target:

```bash
git commit -m "feat: add mock Amazon onboarding workflow"
```

### Slice 4 — Polished Inventory Command Center UI

Goal: make `/demo` look closer to a real product: inventory tracking, planning, Amazon onboarding, and FIFO close all in one coherent workflow.

Files likely modified:

- `cogs-dashboard/src/pages/DemoPage.js`
- `cogs-dashboard/src/demoData.js`
- `cogs-dashboard/src/App.test.js`
- optional: `cogs-dashboard/src/components/demo/*`

UI should include:

- Hero: `FirstLot Inventory Command Center`
- Safety pill: local/demo/fixture only; no Seller Central/SP-API calls; no DB writes.
- Mock Amazon onboarding timeline:
  1. Connect Amazon
  2. Pull SKUs and available inventory
  3. Confirm other warehouses
  4. Upload outside-Amazon SKU/counts
  5. Upload source-backed purchase lots/freight
  6. Match current in-stock to lots
  7. Propose FIFO day 0
- Inventory tracking table:
  - SKU
  - Amazon available
  - other warehouse available
  - total available
  - inbound
  - valuation
  - status/action
- Planning/replenishment table:
  - velocity
  - lead time
  - cover days
  - stockout risk
  - recommendation
- Existing COGS/failure/rerun/month-history sections preserved but framed as downstream close workflows.

Update tests that previously forbade inventory/planning/Amazon terms. The product direction changed; tests should now assert these sections exist while still asserting no fetch/network calls.

Verification:

```bash
cd cogs-dashboard
CI=true npm test -- --watchAll=false
npm run build
```

Commit target:

```bash
git commit -m "feat: polish FirstLot inventory command center demo"
```

### Slice 5 — Cleanup and full verification

- Resolve `docs/plans/firstlot-0205-checkpoint-2026-06-07.md`: commit as historical checkpoint or fold into a final Sunday checkpoint doc.
- Add final build checkpoint:
  - `docs/plans/firstlot-sunday-build-checkpoint-2026-06-07.md`

Full verification:

```bash
make check-firstlot-demo
make check-firstlot-weekend
cd cogs-dashboard && CI=true npm test -- --watchAll=false && npm run build
```

Final report should include:

- branch
- commits
- tests and exact results
- what is product-real vs mock/demo-only
- open questions for Jeff:
  - when to start FIFO/day 0
  - how far Amazon sales history can be pulled
  - what counts as source-backed enough for purchase lots/freight
  - how to treat non-Amazon warehouse counts
  - when to request live Amazon connector approval

---

## FIFO day 0 product rule draft

Until Jeff reviews, treat FIFO day 0 as a proposed, review-required reconstruction point:

- Day 0 should be the earliest date where current in-stock by SKU can be reconciled to source-backed lots/freight with tolerable exceptions.
- If historical sales are available from Amazon, roll current inventory backward month-by-month using sales movements and uploaded purchase lots.
- Stop rollback when any of these block confidence:
  - missing purchase lot/freight source docs
  - unmatched current in-stock units
  - sales history unavailable or incomplete
  - non-Amazon warehouse counts are unknown
  - returns/adjustments materially affect SKU counts
- Output should not claim truth; it should say:
  - proposed start date
  - confidence / blocker status
  - unmatched SKUs/units
  - source docs needed
  - safe next operator action

This is a product/accounting workflow aid, not an accounting judgment. Jeff reviews before real-client reliance.
