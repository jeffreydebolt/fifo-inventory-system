# FirstLot second synthetic client fixture

This is a tiny, fake client-style fixture for testing the generic local client workflow.
It is synthetic data only: no Storage Standard files, no live Supabase/API calls, no `.env`, and no production/client mutation.

Use it to sanity-check a clean month close with multiple SKUs and multi-lot FIFO allocation before trying another local CSV export.

```bash
python3 scripts/run_firstlot_client_fixture.py \
  --fixture-dir tests/fixtures/firstlot_second_synthetic_client \
  --out /tmp/firstlot-second-synthetic-client \
  --period 2026-06 \
  --expect-clear
```

Expected high-level result:

- validation passes,
- FIFO run writes local artifacts only,
- failed SKU queue is clear,
- total COGS is `723.00`,
- remaining inventory value is `485.50`.
