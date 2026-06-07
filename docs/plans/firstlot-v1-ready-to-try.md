# FirstLot v1 ready-to-try checklist

_Last updated: 2026-06-07 by autonomous/local-demo builder loop._

## Current verdict

**Status: not yet v1-ready, but the local/demo spine is close.** The deterministic FIFO engine, local CSV CLI, synthetic demo artifacts, close packet, failed-SKU queue, dashboard `/demo`, and Printing Press-style pre-merge gate all exist. The remaining blocker is not live integration; it is packaging the try path into a single reviewer-grade handoff and keeping every required surface covered by local/demo tests.

## Exact local try path available now

From the repo root, with no credentials and no network required for the FIFO run:

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
| CLI/docs tell Jeff exactly how to try it. | PARTIAL | `docs/local-demo-cli.md` plus command above. | Add one-command reviewer handoff target and put it in the top-level try instructions. |
| Outputs include month-end COGS summary, remaining layers, audit/detail, failed SKU/shortfall queue, close packet, and human-readable summaries. | PASS | `cogs_summary`, `remaining_layers`, `audit_trail`, `cogs_detail`, `shortfalls`, `failed_sku_queue`, `close_packet.md`, month-history/fixed-rerun artifacts. | None for synthetic demo. |
| Dashboard `/demo` presents the command center clearly: Amazon mock boundary, source queue, day-zero basis/blockers, inventory planning/replenishment, run comparison/history, and close packet readiness. | PASS | `cogs-dashboard/src/pages/DemoPage.js`, `cogs-dashboard/src/demoData.js`, dashboard smoke test. | Keep copy aligned with this checklist as the demo evolves. |
| Day-zero/start-date reconstruction is mock/local and visibly blocked until source docs/operator approval; no accounting judgment is implied. | PASS | Day-zero/source queue docs and `/demo` day-zero sections. | None for v1 demo; human approval remains required for real policy/source decisions. |
| Printing Press-style merge readiness process is in place and green. | PASS | `.github/pull_request_template.md`, `scripts/generate_firstlot_merge_packet.py`, `make firstlot-merge-packet`, `make check-firstlot-merge-safety`, `.github/workflows/firstlot-premerge.yml`. | Must keep green on every PR/main. |
| Tests cover core engine/CLI/demo/onboarding/merge-gate/readiness-packet/UI smoke. | PARTIAL | Weekend suite and dashboard smoke exist. | Add/keep explicit readiness-checklist coverage so this file does not disappear or go stale. |
| `make check-firstlot-weekend`, `make check-firstlot-merge-safety`, and GitHub checks pass on latest PR/main. | PARTIAL | Local gates are runnable; PR/main status must be checked per branch. | Verify on current branch before merge and on main after merge. |
| Safety boundary is explicit. | PASS | This file, `AGENTS.md`, CLI docs, merge safety gate, demo scripts. | None. |

## V1 blockers before telling Jeff “ready to try”

1. Add an explicit one-command local handoff target that writes both failing and fixed-rerun demo packets to `/tmp` and prints the inspection paths.
2. Add automated coverage that this readiness checklist exists and names every required v1 surface.
3. Run and record `make check-firstlot-weekend`, `make check-firstlot-merge-safety`, and GitHub PR checks on the latest branch.
4. After merge, verify current `main` with `make check-firstlot-weekend` and recent `gh run list --branch main --limit 5`.

## Next smallest safe bricks

- Add `make firstlot-demo-run` for Jeff/reviewer handoff.
- Add a unit test for this readiness document and include it in the weekend suite.
- Update `docs/local-demo-cli.md` to point first-time reviewers to the one-command handoff target.
