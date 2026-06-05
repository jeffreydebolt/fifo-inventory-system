# FirstLot weekend test readiness — 2026-06-05 04:30

This checkpoint adds a bounded local guardrail for the weekend test lane. It is fixture-only and does not read `.env`, import live services, mutate Supabase, mutate Storage Standard/client data, or deploy anything.

## New guardrail

Run before committing local test/demo changes:

```bash
make check-no-client-data-commit
```

The guard inspects staged data-like files only (`.csv`, `.json`, `.jsonl`, `.log`, `.txt`, `.tsv`) and blocks obvious client/live data markers such as:

- `Storage Standard`
- `cli_`
- `inv_`
- `paydis_`
- `BANK ACCOUNT`
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE`

It also blocks re-adding common live/client export filenames such as `analysis.csv` and Supabase FIFO processing logs.

## Weekend smoke target

Run the combined weekend-ready local suite:

```bash
make check-firstlot-weekend
```

This runs:

1. `make check-no-client-data-commit`
2. Targeted FirstLot unit tests for local CLI, demo artifacts, failed SKU workflow, CSV validation, close packets, and the commit guard.
3. `scripts/check_firstlot_demo.py`, including artifact regeneration from synthetic fixtures and the dashboard smoke test.

## Scope notes for 06:05 report

- Safe/local only: yes.
- Live DB writes: none.
- `.env`/secrets reads: none.
- Storage Standard/client-data mutation: none.
- Deploy: none.
- Primary addition: staged-data guard plus `make check-firstlot-weekend` readiness target.

## Remaining risk

The repo still contains historical live-derived files that predate this checkpoint. This guard is intentionally focused on preventing new staged client/live data from entering future commits. A separate reviewed cleanup PR should decide how to quarantine/remove historical files without disrupting traceability.
