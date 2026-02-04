# Support Macros & Scripts

Quick reference for FIFO COGS system operations scripts.

## Overview

All scripts are located in `/scripts/` and should be run from the project root.

## Daily Operations

### `daily_health_check.sh`

**Purpose:** Verify overall system health - API, dashboard, database.

**When to use:** 
- Run daily (via cron or manually)
- When investigating reported issues
- After deployments

**Usage:**
```bash
./scripts/daily_health_check.sh
```

**What it checks:**
- API health endpoint (`/healthz`)
- Dashboard availability
- Database connectivity
- Recent COGS runs (last 24h)
- Error rates

**Environment variables:**
- `FIFO_API_URL` - API endpoint (default: production URL)
- `FIFO_DASHBOARD_URL` - Dashboard URL (default: production URL)
- `SUPABASE_URL` - Database connection string

---

### `weekly_metrics.sh`

**Purpose:** Generate weekly usage and performance metrics.

**When to use:**
- Weekly reporting
- Capacity planning
- Performance trend analysis

**Usage:**
```bash
./scripts/weekly_metrics.sh
```

**Output includes:**
- Active tenant count
- Total runs (success/fail/rollback)
- Failure analysis by error type
- Top active tenants
- Database size by table
- Processing time statistics

**Requirements:**
- `SUPABASE_URL` must be set

---

## Security Operations

### `check_key_expiry.sh`

**Purpose:** Check if secrets/keys are approaching rotation deadline.

**When to use:**
- Weekly (automated or manual)
- Before going on vacation
- Compliance audits

**Usage:**
```bash
./scripts/check_key_expiry.sh
```

**Configuration:**
- Reads `docs/SECRETS_ROTATION.md` for last rotation dates
- Default policy: 90-day rotation
- Warning threshold: 14 days before expiry

**Exit codes:**
- `0` - All keys within policy
- `1` - One or more keys need attention

---

### `emergency_key_rotation.sh`

**Purpose:** Interactive guide for emergency key rotation.

**When to use:**
- Key compromise suspected
- Security incident response
- Urgent rotation needed

**Usage:**
```bash
./scripts/emergency_key_rotation.sh
```

**Steps covered:**
1. Generate new Supabase key
2. Update API server environment
3. Verify API health
4. Update dashboard (if applicable)
5. Revoke old keys
6. Document rotation

**Output:**
- Creates timestamped log file: `key_rotation_YYYYMMDD_HHMMSS.log`

---

## Backup & Recovery

### `backup_health_check.sh`

**Purpose:** Verify backup systems are functioning.

**When to use:**
- Daily/weekly verification
- Before major changes
- Disaster recovery planning

**Usage:**
```bash
./scripts/backup_health_check.sh
```

**What it checks:**
- Supabase automatic backup status (Pro plan)
- Local backup file age (if configured)
- Restore documentation exists
- Basic data integrity

**Configuration:**
- `BACKUP_DIR` - Local backup directory (default: `./backups`)
- `MAX_BACKUP_AGE_HOURS` - Critical threshold (default: 24)
- `WARNING_AGE_HOURS` - Warning threshold (default: 12)

---

### `rollback_and_rerun.sh`

**Purpose:** Rollback a failed run and reprocess with corrected data.

**When to use:**
- After discovering data errors post-processing
- When a run produced incorrect results
- Recovery from partial failures

**Usage:**
```bash
./scripts/rollback_and_rerun.sh <RUN_ID> <CORRECTED_SALES_FILE>
```

**Example:**
```bash
./scripts/rollback_and_rerun.sh RUN_123456 sales_corrected.csv
```

---

## Data Validation

### `csv_validation_response.sh`

**Purpose:** Diagnose CSV upload failures and provide fix guidance.

**When to use:**
- User reports upload failure
- Validation errors in logs
- Preparing data for upload

**Usage:**
```bash
./scripts/csv_validation_response.sh <csv_file> [lots|sales]
```

**Examples:**
```bash
./scripts/csv_validation_response.sh my_sales.csv sales
./scripts/csv_validation_response.sh inventory.csv lots
```

**Checks performed:**
- UTF-8 BOM detection
- File encoding verification
- Required columns present
- Date format validation
- Row consistency (column counts)
- Empty row detection

**Output:**
- Detailed error messages
- Specific fix instructions
- Example valid format

---

## Quick Reference

| Script | Frequency | Requires DB | Interactive |
|--------|-----------|-------------|-------------|
| `daily_health_check.sh` | Daily | Optional | No |
| `weekly_metrics.sh` | Weekly | Yes | No |
| `check_key_expiry.sh` | Weekly | No | No |
| `emergency_key_rotation.sh` | As needed | No | Yes |
| `backup_health_check.sh` | Daily/Weekly | Optional | No |
| `rollback_and_rerun.sh` | As needed | Yes | No |
| `csv_validation_response.sh` | As needed | No | No |

---

## Setting Up Automated Runs

### Cron Examples

```bash
# Daily health check at 8 AM
0 8 * * * cd /path/to/fifo-inventory-system && ./scripts/daily_health_check.sh >> /var/log/fifo-health.log 2>&1

# Weekly metrics on Monday at 9 AM
0 9 * * 1 cd /path/to/fifo-inventory-system && ./scripts/weekly_metrics.sh >> /var/log/fifo-metrics.log 2>&1

# Weekly key expiry check on Friday at 10 AM
0 10 * * 5 cd /path/to/fifo-inventory-system && ./scripts/check_key_expiry.sh || echo "Key rotation needed" | mail -s "FIFO Key Alert" admin@example.com
```

### Environment Setup

Create a `.env` file in the project root:

```bash
SUPABASE_URL=postgresql://user:pass@host:5432/db
FIFO_API_URL=https://fifo-cogs-api.onrender.com
FIFO_DASHBOARD_URL=https://fifo-cogs-dashboard.vercel.app
BACKUP_DIR=./backups
```

---

## Troubleshooting

### Scripts won't run
```bash
# Make executable
chmod +x scripts/*.sh
```

### Database connection fails
- Verify `SUPABASE_URL` is set correctly
- Check network/firewall access
- Verify credentials haven't been rotated

### Health check false positives
- Verify URLs in environment variables
- Check if services are in maintenance mode
- Review recent deployments

---

*Last updated: 2026-02-03*
