# FirstLot v1 ready-to-try checklist

_Last updated: 2026-06-08 by autonomous/local-demo builder loop._

## Current verdict

**Status: v1-ready for a local/demo try on current `main` after post-merge verification.** The deterministic FIFO engine, local CSV CLI, one-command synthetic demo packet, close packet, failed-SKU queue, dashboard `/demo`, readiness checklist coverage, and Printing Press-style pre-merge gate all exist. The v1 boundary remains local/demo only; real Amazon, live database, Storage Standard, and accounting-policy decisions stay out of scope.

## Exact local try path available now

From the repo root, with no credentials and no network required for the FIFO run:

```bash
make firstlot-demo-run
```

Equivalent lower-level command:

```bash
python3 scripts/regenerate_firstlot_demo_artifacts.py \
  --out /tmp/firstlot-demo-v1 \
  --fixed-out /tmp/firstlot-demo-fixed
```

Then inspect:

- `/tmp/firstlot-demo-v1/cogs_summary.csv`
- `/tmp/firstlot-demo-v1/remaining_layers.csv`
- `/tmp/firstlot-demo-v1/audit_trail.csv`
- `/tmp/firstlot-demo-v1/failed_sku_queue.csv`
- `/tmp/firstlot-demo-v1/close_packet.md`
- `/tmp/firstlot-demo-fixed/month_history.csv`
- `/tmp/firstlot-demo-fixed/close_packet.md`

Dashboard demo path:

```bash
cd cogs-dashboard
npm test -- --runTestsByPath src/App.test.js --watchAll=false
npm start
```

Open `http://localhost:3000/demo`. The page is fixture-backed only; controls are display/prototype state and do not upload files or call live services.

## Safety boundary

FirstLot v1 trial mode is explicitly local/demo only:

- no `.env` reads, sourcing, or printing;
- no live Amazon, SP-API, Seller Central, OAuth, or credential flow;
- no live DB, Supabase, or production API writes;
- no Storage Standard/client-data mutation;
- no real client CSV/export commits;
- dangerous data scripts remain source-only unless Jeff explicitly approves.

## Readiness checklist

| Requirement | State | Evidence | Remaining blocker |
| --- | --- | --- | --- |
| Local/demo FirstLot flow can run end-to-end from synthetic fixtures with no network/live data. | PASS | `python3 scripts/regenerate_firstlot_demo_artifacts.py --out /tmp/firstlot-demo-v1 --fixed-out /tmp/firstlot-demo-fixed`; `make check-firstlot-demo`. | None for CLI artifacts. |
| CLI/docs tell Jeff exactly how to try it. | PASS | `make firstlot-demo-run`, `docs/local-demo-cli.md`, and the command above. | None for local/demo try. |
| Outputs include month-end COGS summary, remaining layers, audit/detail, failed SKU/shortfall queue, close packet, and human-readable summaries. | PASS | `cogs_summary`, `remaining_layers`, `audit_trail`, `cogs_detail`, `shortfalls`, `failed_sku_queue`, `close_packet.md`, month-history/fixed-rerun artifacts. | None for synthetic demo. |
| Dashboard `/demo` presents the command center clearly: Amazon mock boundary, source queue, day-zero basis/blockers, inventory planning/replenishment, run comparison/history, and close packet readiness. | PASS | `cogs-dashboard/src/pages/DemoPage.js`, `cogs-dashboard/src/demoData.js`, dashboard smoke test. | Keep copy aligned with this checklist as the demo evolves. |
| Day-zero/start-date reconstruction is mock/local and visibly blocked until source docs/operator approval; no accounting judgment is implied. | PASS | Day-zero/source queue docs and `/demo` day-zero sections. | None for v1 demo; human approval remains required for real policy/source decisions. |
| Printing Press-style merge readiness process is in place and green. | PASS | `.github/pull_request_template.md`, `scripts/generate_firstlot_merge_packet.py`, `make firstlot-merge-packet`, `make check-firstlot-merge-safety`, `.github/workflows/firstlot-premerge.yml`. | Must keep green on every PR/main. |
| Tests cover core engine/CLI/demo/onboarding/merge-gate/readiness-packet/UI smoke. | PASS | `make check-firstlot-weekend` includes explicit readiness-checklist coverage plus engine/CLI/demo/merge/readiness-packet tests; dashboard smoke is exercised by `make check-firstlot-demo`. | Keep green as v1 evolves. |
| `make check-firstlot-weekend`, `make check-firstlot-merge-safety`, and GitHub checks pass on latest PR/main. | PASS once latest PR/main verification is recorded below | Local gates are the required branch/main checks; GitHub checks are inspected before merge and after main update. | Per-run verification remains required before declaring the specific commit ready. |
| Safety boundary is explicit. | PASS | This file, `AGENTS.md`, CLI docs, merge safety gate, demo scripts. | None. |

## V1 verification required on the latest commit before telling Jeff “ready to try”

1. Run and record `make firstlot-demo-run`, `make check-firstlot-weekend`, and branch-only `make check-firstlot-merge-safety` on the latest non-main branch.
2. Open/merge a bounded local-demo PR only after GitHub checks are green and no human review gate is triggered.
3. After merge, verify current `main` with `make firstlot-demo-run`, `make check-firstlot-weekend`, and recent `gh run list --branch main --limit 5`. Do not run the merge-safety gate directly on `main`; by design it fails closed there to prevent direct-main work.

## Next smallest safe bricks

- Keep the one-command handoff and readiness checklist synchronized with any CLI/dashboard changes.
- Add final reviewer-facing screenshots or short demo transcript only if Jeff asks; do not add live connector scope.
