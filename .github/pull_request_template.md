## Summary

- 

## FirstLot pre-merge readiness

Before merge, this PR must have a readiness packet and pass the merge gate.

Required local command for autonomous/bounded branches:

```bash
make check-firstlot-merge-safety
```

Optional packet command:

```bash
make firstlot-merge-packet
```

## Safety boundary checklist

- [ ] Fixture/local/demo-only unless explicitly stated otherwise.
- [ ] No `.env` reads/sourcing/printing.
- [ ] No live Amazon/Seller Central/SP-API/OAuth calls.
- [ ] No live DB/Supabase/API writes.
- [ ] No Storage Standard/client data mutation.
- [ ] No real client CSV/export committed.
- [ ] No rollback/upload/delete/migrate/clean/fix live-data scripts executed.

## Verification

Paste exact output or summarize with run links:

- [ ] `make check-firstlot-merge-safety`
- [ ] GitHub `FirstLot pre-merge readiness` check
- [ ] GitHub API/dashboard/demo checks as applicable
- [ ] Netlify/Vercel/deploy-preview status classified if UI changed
- [ ] Post-merge main verification plan stated if this PR will be auto-merged

## Human review gates

Leave this PR open for Jeff if any apply:

- live Amazon connector / OAuth / SP-API / credential path
- live DB/API/Supabase write path
- client data or Storage Standard mutation
- accounting/FIFO day-zero acceptance rule beyond mock/readiness UX
- production deploy behavior not clearly green
- unclear UX/product direction

## Merge rule

Squash-merge only when:

1. readiness packet has no blockers,
2. `make check-firstlot-merge-safety` passes,
3. GitHub checks pass,
4. work is bounded/local-demo/no-live-work,
5. no human review gate is triggered.
