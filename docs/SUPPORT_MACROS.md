# Support Macros Documentation

Quick reference for FIFO COGS support scripts.

## rollback.sh

Rollback a completed FIFO COGS run.

**Usage:**
```bash
./scripts/rollback.sh <RUN_ID> [--confirm]
```

**Arguments:**
- `RUN_ID` - The run ID to rollback (e.g., RUN_123456)
- `--confirm` - Required to perform actual rollback (dry run by default)

**Examples:**
```bash
# Dry run (shows what would happen)
./scripts/rollback.sh RUN_123456

# Actual rollback
./scripts/rollback.sh RUN_123456 --confirm
```

**Exit Codes:**
- `0` - Success
- `1` - Run not found, rollback failed, or missing arguments

**Environment Variables:**
- `SUPABASE_URL` - Direct database connection (optional)
- `API_URL` - API endpoint (default: http://localhost:8000)

---

## rerun.sh

Start a new FIFO COGS calculation run.

**Usage:**
```bash
./scripts/rerun.sh --tenant-id TENANT --mode MODE --start-month YYYY-MM-01 [OPTIONS]
```

**Required Arguments:**
- `--tenant-id` - Tenant identifier
- `--mode` - Calculation mode: `fifo` or `avg`
- `--start-month` - Start month in YYYY-MM-01 format

**Optional Arguments:**
- `--sales-file` - Path to sales CSV file
- `--lots-file` - Path to lots CSV file

**Examples:**
```bash
# Basic run without files (uses existing data)
./scripts/rerun.sh --tenant-id acme-corp --mode fifo --start-month 2024-07-01

# Run with CSV files
./scripts/rerun.sh \
  --tenant-id acme-corp \
  --mode fifo \
  --start-month 2024-07-01 \
  --sales-file sales_july.csv \
  --lots-file inventory.csv
```

**Exit Codes:**
- `0` - Run completed successfully
- `1` - Run failed, invalid arguments, or timeout

**Features:**
- Prints run_id immediately after starting
- Polls status every 5 seconds
- 5-minute timeout for completion
- Converts CSV files to JSON automatically

---

## csv_validate.sh

Validate CSV files before processing.

**Usage:**
```bash
./scripts/csv_validate.sh <TYPE> <FILE>
```

**Arguments:**
- `TYPE` - File type: `sales` or `lots`
- `FILE` - Path to CSV file

**Examples:**
```bash
# Validate sales CSV
./scripts/csv_validate.sh sales sales_2024.csv

# Validate lots CSV
./scripts/csv_validate.sh lots inventory_lots.csv
```

**Exit Codes:**
- `0` - Validation passed
- `1` - Validation failed or invalid arguments

**Sales CSV Required Headers:**
- `sale_id`
- `sku`
- `sale_date` (format: YYYY-MM-DD)
- `quantity_sold`

**Lots CSV Required Headers:**
- `lot_id`
- `sku`
- `received_date` (format: YYYY-MM-DD)
- `original_quantity`
- `remaining_quantity`
- `unit_price`
- `freight_cost_per_unit`

**Validation Checks:**
- Missing required headers (shows exact missing columns)
- Date format validation
- Empty values detection
- Numeric field validation (lots only)
- Provides example CSV format on failure

---

## Quick Troubleshooting

**Common Issues:**

1. **"File not found"** - Check file path and ensure file exists
2. **"Missing required headers"** - Script shows exact headers needed
3. **"Invalid date format"** - Use YYYY-MM-DD format (e.g., 2024-07-20)
4. **"Run timeout"** - Check API health and database connectivity

**Making Scripts Executable:**
```bash
chmod +x scripts/*.sh
```