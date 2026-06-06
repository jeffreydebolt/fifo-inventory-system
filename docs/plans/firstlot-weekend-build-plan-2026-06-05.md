# FirstLot Weekend Build Plan — 2026-06-05

> **For Hermes:** Use subagent-driven-development skill or focused branch/PR cycles to implement this plan task-by-task. Keep the main chat command/control only.

**Goal:** Make FirstLot weekend-testable for Jeff using raw client-shaped CSVs, with a clean operator flow from upload/selection → smoke run → close packet review → failed-SKU repair/rerun.

**Architecture:** Stay local/demo-only through the weekend. Build on the shipped deterministic FIFO engine, `client-smoke` runner, CSV normalizers, close packet, failed-SKU fix plan, and no-client-data guard. Do not add live connectors, production DB writes, or roadmap UI theater.

**Tech Stack:** Python 3.11 local CLI/tests, pytest, React demo UI/Jest, GitHub PR checkpoints, `/tmp` output artifacts only for real/client-shaped smoke runs.

---

## Current baseline

Repo: `/Users/jeffdebolt/clawd/projects/fifo-inventory-system`

Current `main`: `b9e2832b feat: add FirstLot client smoke runner (#19)`

Already shipped and green:

- #14 local client-test fixture selector
- #15 test hardening / client-data commit guard
- #16 weekend CSV test packet
- #17 staged `.env`/client-data guard
- #18 client-shaped lots/sales normalizers
- #19 one-command `client-smoke` runner

Current safe verification command:

```bash
make check-firstlot-weekend
```

Expected current result:

```text
36 passed
FirstLot local demo safe check passed
```

Actual uploaded sample result from Jeff’s lot + Sept 2025 sales CSVs:

```json
{
  "period": "2025-09",
  "total_cogs": "269.55",
  "failed_sku_count": 1,
  "total_shortfall_quantity": 1,
  "needed_fix": "CP510342BK short 1 unit; reason NO_INVENTORY"
}
```

---

## Weekend success definition

By the end of the weekend, Jeff should be able to:

1. Pick/copy raw lots and sales CSVs into a local scratch folder.
2. Run one command or use a simple local/demo UI flow.
3. Get normalized strict FirstLot CSVs.
4. Get a month-close packet with:
   - total COGS,
   - SKU-level COGS detail,
   - remaining layers,
   - audit trail,
   - failed SKU queue,
   - fix/rerun plan.
5. See exactly what blocked a clean close.
6. Fix local CSVs or add source-backed missing lots.
7. Rerun the same period with a version/history trail.
8. Keep all real client CSVs and generated client artifacts out of git and live systems.

Non-goals this weekend:

- no live Supabase writes;
- no `.env` or secret usage;
- no Storage Standard mutation;
- no Amazon/Shopify/API connector work;
- no tax/accounting conclusions;
- no production deploy dependency;
- no demand planning, forecasting, or roadmap UI.

---

## Build lane order

### Lane 1 — Operator UX: make `client-smoke` impossible to misuse

**Objective:** Turn the current CLI into a clearer operator experience for Jeff’s weekend test.

**Branch:** `feat/firstlot-client-smoke-operator-ux`

**Files:**

- Modify: `core/client_smoke.py`
- Modify: `app/local_cli.py`
- Modify/Test: `tests/unit/test_client_smoke_runner.py`
- Modify docs: `docs/firstlot-weekend-client-csv-test-packet.md`

**Tasks:**

1. Add `--json-out` option to `client-smoke` so summary can be written to an explicit path while still printing concise terminal output.
2. Add a concise human terminal summary after JSON write:
   - period,
   - total COGS,
   - failed SKU count,
   - output folder,
   - next command.
3. Add test proving `--json-out /tmp/foo.json` writes the same payload as `client_smoke_summary.json`.
4. Add test proving `--expect-clear` prints a clear failure summary when failed SKUs remain.
5. Add docs section: “What Jeff should run first.”

**Verification:**

```bash
python3 -m pytest tests/unit/test_client_smoke_runner.py -q
make check-firstlot-weekend
```

**Acceptance:** PR opened and merged only after local + GitHub checks pass.

---

### Lane 2 — Source-backed missing-lot repair workflow

**Objective:** Convert failed SKU output into a practical local repair packet without implying fake COGS.

**Branch:** `feat/firstlot-source-backed-repair-packet`

**Files:**

- Modify: `core/client_smoke.py`
- Modify: `core/failed_sku_workflow.py`
- Add/Modify tests: `tests/unit/test_failed_sku_workflow.py`, `tests/unit/test_client_smoke_runner.py`
- Docs: `docs/firstlot-weekend-client-csv-test-packet.md`

**Tasks:**

1. Add a `missing_lot_request.csv` artifact when failed SKUs remain.
2. Columns:
   - `sku`,
   - `period`,
   - `minimum_units_needed`,
   - `first_sale_date`,
   - `last_sale_date`,
   - `reason`,
   - `source_document_needed`,
   - `operator_note`.
3. Keep `synthetic_repair_lots_SANDBOX_ONLY.csv`, but move it below the source-backed artifact in docs and summary.
4. Add tests for the artifact with one failed SKU.
5. Add docs: synthetic rows are shape tests only; COGS requires source-backed lot/cost evidence.

**Verification:**

```bash
python3 -m pytest tests/unit/test_failed_sku_workflow.py tests/unit/test_client_smoke_runner.py -q
make check-firstlot-weekend
```

**Acceptance:** Failed SKU output tells Jeff exactly what source-backed purchase-lot data is needed next.

---

### Lane 3 — Real uploaded sample replay fixture, sanitized

**Objective:** Preserve the shape of Jeff’s actual CSV issue without committing client data.

**Branch:** `feat/firstlot-sanitized-september-replay-fixture`

**Files:**

- Add: `tests/fixtures/firstlot_client_exports/sept_replay_lots_sanitized.csv`
- Add: `tests/fixtures/firstlot_client_exports/sept_replay_sales_sanitized.csv`
- Add/Modify: `tests/unit/test_client_smoke_runner.py`
- Docs: `docs/firstlot-weekend-client-csv-test-packet.md`

**Tasks:**

1. Create tiny sanitized fixture with the same schema quirks as Jeff’s upload:
   - `po_number`,
   - `original_unit_qty`,
   - `remaining_unit_qty`,
   - M/D/YY dates,
   - `$` currency,
   - comma quantities,
   - sales with `SKU`, `Quantity_Sold`, `Sale_Month_Str`, no `sale_id`.
2. Include one intentionally missing SKU to exercise failed queue.
3. Use only synthetic SKU names like `DEMO-SEPT-001`.
4. Test that `client-smoke --expect-clear` fails with one missing SKU.
5. Test that without `--expect-clear`, artifacts are written and `ok: true` with `failed_sku_count: 1`.

**Verification:**

```bash
python3 -m pytest tests/unit/test_client_smoke_runner.py -q
make check-firstlot-weekend
```

**Acceptance:** Future changes cannot break the exact class of upload Jeff just tested.

---

### Lane 4 — Local/demo UI wrapper for the smoke runner

**Objective:** Give Jeff a simple UI path without touching live systems.

**Branch:** `feat/firstlot-local-smoke-ui`

**Files:**

- Inspect/Modify: `cogs-dashboard/src/App.js`
- Inspect/Modify: `cogs-dashboard/src/App.test.js`
- Possibly add: local static demo component under `cogs-dashboard/src/`
- Docs: `docs/firstlot-weekend-client-csv-test-packet.md`

**Tasks:**

1. Add a “Weekend Client Smoke” section to the demo UI.
2. Keep it explicit that browser upload is demo/local guidance unless backed by a local process; do not fake live processing.
3. Show copy/paste command generated from:
   - lot path,
   - sales path,
   - period,
   - output path.
4. Show expected artifact list and failed-SKU review checklist.
5. Add Jest tests confirming:
   - no production fetch/API call,
   - safety copy appears,
   - generated command includes `client-smoke`, `--period`, `--clean-output`.

**Verification:**

```bash
python3 scripts/check_firstlot_demo.py
make check-firstlot-weekend
```

**Acceptance:** UI helps Jeff run the local workflow, but does not pretend to upload/process client files in-browser.

---

### Lane 5 — Rerun/version comparison

**Objective:** Make fix-and-rerun review obvious after a missing lot is repaired.

**Branch:** `feat/firstlot-rerun-diff-summary`

**Files:**

- Modify: `core/month_history.py`
- Modify: `core/close_packet.py`
- Modify: `app/local_cli.py`
- Tests: `tests/unit/test_month_history_workflow.py`, `tests/unit/test_close_packet.py`

**Tasks:**

1. Add a read-only `diff-runs` command if existing history has multiple runs for one period.
2. Compare:
   - prior total COGS,
   - new total COGS,
   - failed SKU count,
   - affected SKUs.
3. Add diff section to close packet when `--reopen` writes a new history row.
4. Add tests using synthetic rerun with fixed lot.
5. Document “rerun after source-backed fix” flow.

**Verification:**

```bash
python3 -m pytest tests/unit/test_month_history_workflow.py tests/unit/test_close_packet.py -q
make check-firstlot-weekend
```

**Acceptance:** Jeff can see before/after impact of a missing-lot fix without trusting memory.

---

### Lane 6 — Historical live-script quarantine review

**Objective:** Reduce repo risk from old dangerous scripts without deleting traceability blindly.

**Branch:** `chore/firstlot-quarantine-dangerous-scripts-plan`

**Files:**

- Add: `docs/audits/firstlot-dangerous-script-inventory-2026-06-06.md`
- Possibly modify: `AGENTS.md` or guard tests only after review

**Tasks:**

1. Inventory files matching dangerous names:
   - `upload_*`,
   - `delete_*`,
   - `rollback_*`,
   - `restore_*`,
   - `migrate_*`,
   - `clean_*`,
   - `*_supabase*`.
2. Classify each as:
   - read-only inspect,
   - likely live mutation,
   - unknown.
3. Do not run them.
4. Propose quarantine options:
   - move to `legacy-dangerous/`,
   - add README warnings,
   - add CI/guard to block invoking them,
   - archive/delete only after Jeff approval.

**Verification:**

```bash
git status --short
make check-no-client-data-commit
```

**Acceptance:** Safer repo posture without breaking historical traceability or running live scripts.

---

## Weekend operating cadence

Use small PR checkpoints, not one monster branch.

Recommended sequence:

1. Friday night / first build block: Lane 1 + Lane 2.
2. Saturday morning: Lane 3 + run Jeff’s uploaded sample through current `client-smoke` again.
3. Saturday afternoon: Lane 4 UI helper.
4. Saturday evening: Lane 5 rerun diff if the core path is stable.
5. Sunday: Lane 6 audit/quarantine plan and polish docs.

After each PR:

```bash
git checkout main
git pull --ff-only origin main
make check-firstlot-weekend
```

Then open PR, watch checks, and merge only when Jeff has delegated merge authority for that bounded slice or explicitly approves.

---

## Stop/ask boundaries

Stop and ask Jeff before:

- reading or printing secrets;
- sourcing `.env`;
- mutating Supabase/live DB;
- mutating Storage Standard/client data;
- sending client artifacts outside this chat/machine;
- committing real client CSVs or generated client artifacts;
- deleting/quarantining historical live scripts;
- making accounting/tax conclusions from COGS output.

---

## Final weekend report format

Use this format after the weekend build block:

```markdown
## FirstLot weekend build report

- Main commit:
- PRs shipped:
- Local verification:
- GitHub verification:
- Jeff sample replay:
- Failed SKU status:
- Artifacts generated:
- What Jeff can test now:
- Remaining blockers:
- Safety confirmation:
```
