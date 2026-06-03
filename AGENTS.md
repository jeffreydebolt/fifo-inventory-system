# AGENTS.md — FIFO / FirstLot

This repo contains a live/client-derived FIFO inventory system. Treat it as safety-critical.

## Non-negotiable safety rules

1. **No live database writes.** Do not run scripts that insert, update, delete, rollback, upload, migrate, clean, or patch Supabase/live client data.
2. **No `.env` usage.** Do not source or read credential files except to confirm they exist. Never print secrets.
3. **Do not mutate Storage Standard client data.** Work in this public repo only unless Jeff explicitly approves a client-data task.
4. **No main-branch pushes.** Autonomous work must happen on a named branch and be reported for review.
5. **Prefer fixtures/tests over production data.** Use tiny synthetic CSV fixtures under `tests/fixtures/` or `examples/`.
6. **Separate engine from app.** The priority is a deterministic, test-covered FIFO engine/CLI that can become a free GitHub project. Paid UI/reporting comes later.
7. **Before running any command, classify it:** read-only, test-only, local file edit, or live mutation. Never run live mutation commands.

## Dangerous script name patterns

Treat these as read-only source files unless Jeff explicitly approves running one:

- `upload_*`
- `delete_*`
- `rollback_*`
- `restore_*`
- `migrate_*`
- `clean_*`
- `fix_*anomal*`
- `*_supabase*` when it could write
- anything that imports live Supabase credentials or writes to a database

## Nightly autonomous lane

The nightly lane should:

1. Inspect current repo state and PR #3 history.
2. Work on branch `autonomous/fifo-nightly` or a dated branch under `autonomous/`.
3. Build small, testable pieces toward:
   - pure FIFO engine
   - CLI from CSV fixtures
   - month-end COGS output
   - remaining layers output
   - audit trail output
4. Run tests locally.
5. Commit local changes only when tests pass.
6. Report what changed, what tests ran, and what risk remains.

Do not push or open PRs unless Jeff explicitly asks.
