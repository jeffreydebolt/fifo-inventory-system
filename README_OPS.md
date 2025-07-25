# FIFO COGS System - Operations Runbook

## Overview

This runbook covers day-to-day operations, common procedures, troubleshooting, and incident response for the FIFO COGS multi-tenant system.

## System Architecture Quick Reference

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React App     │───▶│   FastAPI       │───▶│   Supabase      │
│   (Vercel)      │    │   (Render/Fly)  │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
    User Browser            API Server              PostgreSQL
    - Authentication        - COGS Engine           - Multi-tenant
    - File Upload          - Rollback Logic         - Row Level Security
    - Dashboard            - Journal Export         - Audit Trail
```

## Daily Operations

### Health Checks (Run Daily)

```bash
#!/bin/bash
# daily_health_check.sh

echo "🏥 FIFO COGS System Health Check - $(date)"
echo "================================================"

# 1. API Health
echo "🔍 Checking API health..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://your-api-url.com/health)
if [ "$API_STATUS" = "200" ]; then
    echo "✅ API is healthy"
else
    echo "❌ API is down (HTTP $API_STATUS)"
fi

# 2. Dashboard Health
echo "🔍 Checking dashboard health..."
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://your-dashboard-url.vercel.app)
if [ "$DASHBOARD_STATUS" = "200" ]; then
    echo "✅ Dashboard is healthy"
else
    echo "❌ Dashboard is down (HTTP $DASHBOARD_STATUS)"
fi

# 3. Database Connectivity
echo "🔍 Checking database connectivity..."
DB_CHECK=$(psql $SUPABASE_URL -t -c "SELECT 1;" 2>/dev/null)
if [ "$DB_CHECK" = " 1" ]; then
    echo "✅ Database is accessible"
else
    echo "❌ Database connection failed"
fi

# 4. Recent Activity
echo "🔍 Checking recent activity..."
RECENT_RUNS=$(psql $SUPABASE_URL -t -c "SELECT COUNT(*) FROM cogs_runs WHERE created_at >= NOW() - INTERVAL '24 hours';" 2>/dev/null)
echo "📊 COGS runs in last 24h: $RECENT_RUNS"

# 5. Error Rate
echo "🔍 Checking error rates..."
ERROR_COUNT=$(psql $SUPABASE_URL -t -c "SELECT COUNT(*) FROM cogs_runs WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '24 hours';" 2>/dev/null)
echo "🚨 Failed runs in last 24h: $ERROR_COUNT"

if [ "$ERROR_COUNT" -gt 5 ]; then
    echo "⚠️  High error rate detected - investigation required"
fi

echo "================================================"
echo "Health check complete"
```

### System Metrics (Run Weekly)

```bash
#!/bin/bash
# weekly_metrics.sh

echo "📊 FIFO COGS Weekly Metrics - $(date)"
echo "======================================"

# Tenant activity
psql $SUPABASE_URL << EOF
SELECT 
    'Active Tenants (7 days)' as metric,
    COUNT(DISTINCT tenant_id) as value
FROM cogs_runs 
WHERE created_at >= NOW() - INTERVAL '7 days';

SELECT 
    'Total Runs (7 days)' as metric,
    COUNT(*) as value
FROM cogs_runs 
WHERE created_at >= NOW() - INTERVAL '7 days';

SELECT 
    'Rollbacks (7 days)' as metric,
    COUNT(*) as value
FROM cogs_runs 
WHERE status = 'rolled_back' 
AND created_at >= NOW() - INTERVAL '7 days';

SELECT 
    'Failed Runs (7 days)' as metric,
    COUNT(*) as value
FROM cogs_runs 
WHERE status = 'failed' 
AND created_at >= NOW() - INTERVAL '7 days';
EOF

# Storage usage
echo "💾 Database size:"
psql $SUPABASE_URL -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## Common Operations

### 1. Running a COGS Calculation

**Via CLI (Recommended for bulk operations)**:
```bash
# Basic run
python -m app.cli run \
  --tenant-id "acme-corp" \
  --sales-file sales_2024.csv \
  --lots-file lots_2024.csv

# Dry run (validation only)
python -m app.cli run \
  --tenant-id "acme-corp" \
  --sales-file sales_2024.csv \
  --dry-run

# With specific mode
python -m app.cli run \
  --tenant-id "acme-corp" \
  --sales-file sales_2024.csv \
  --mode fifo
```

**Via API**:
```bash
curl -X POST https://your-api-url.com/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "acme-corp",
    "mode": "fifo",
    "sales_data": [
      {
        "sale_id": "SALE001",
        "sku": "WIDGET-A",
        "sale_date": "2024-07-20T10:00:00Z",
        "quantity_sold": 100,
        "tenant_id": "acme-corp"
      }
    ],
    "lots_data": [
      {
        "lot_id": "LOT001",
        "sku": "WIDGET-A",
        "received_date": "2024-07-01T00:00:00Z",
        "original_quantity": 500,
        "remaining_quantity": 500,
        "unit_price": 10.00,
        "freight_cost_per_unit": 1.00,
        "tenant_id": "acme-corp"
      }
    ]
  }'
```

### 2. Rolling Back a Run

**When to rollback**:
- Incorrect data was processed
- Calculation errors discovered
- Need to reprocess with corrected data

**Via CLI**:
```bash
# Rollback specific run
python -m app.cli rollback RUN_123456 --confirm

# List recent runs first
python -m app.cli list-runs --tenant-id "acme-corp" --limit 10
```

**Via API**:
```bash
# Rollback
curl -X POST https://your-api-url.com/api/v1/runs/RUN_123456/rollback

# Check status
curl -X GET https://your-api-url.com/api/v1/runs/RUN_123456
```

**Via Dashboard**:
1. Login to dashboard
2. Navigate to Home page
3. Find the run in recent runs
4. Click "Rollback" button
5. Confirm the action

### 3. Re-running After Rollback

**Complete workflow**:
```bash
# 1. List recent runs to find the one to rollback
python -m app.cli list-runs --tenant-id "acme-corp"

# 2. Rollback the problematic run
python -m app.cli rollback RUN_123456 --confirm

# 3. Verify rollback completed
python -m app.cli list-runs --tenant-id "acme-corp" --limit 5

# 4. Re-run with corrected data
python -m app.cli run \
  --tenant-id "acme-corp" \
  --sales-file sales_corrected.csv \
  --lots-file lots_current.csv
```

### 4. Onboarding a New Tenant

**Steps**:
1. **Verify tenant ID format**:
   ```bash
   # Tenant ID should be lowercase, alphanumeric with hyphens
   # Good: "acme-corp", "widgets-inc", "test-tenant"
   # Bad: "Acme Corp", "widgets_inc", "test tenant"
   ```

2. **Create initial user account**:
   - User registers in dashboard with email format: `{tenant-id}@domain.com`
   - System automatically derives tenant ID from email prefix

3. **Upload initial data**:
   ```bash
   # Upload lots (inventory)
   curl -X POST https://your-api-url.com/api/v1/files/lots \
     -F "tenant_id=new-tenant" \
     -F "file=@initial_lots.csv"
   
   # Upload sales data
   curl -X POST https://your-api-url.com/api/v1/files/sales \
     -F "tenant_id=new-tenant" \
     -F "file=@historical_sales.csv"
   ```

4. **Run initial COGS calculation**:
   ```bash
   python -m app.cli run \
     --tenant-id "new-tenant" \
     --sales-file historical_sales.csv \
     --dry-run  # Validate first
   
   # If validation passes:
   python -m app.cli run \
     --tenant-id "new-tenant" \
     --sales-file historical_sales.csv
   ```

5. **Verify tenant isolation**:
   ```bash
   # Check tenant can only see their own data
   curl "https://your-api-url.com/api/v1/runs?tenant_id=new-tenant"
   
   # Verify no cross-tenant data leakage
   psql $SUPABASE_URL -c "
   SELECT tenant_id, COUNT(*) 
   FROM cogs_runs 
   WHERE tenant_id = 'new-tenant' 
   GROUP BY tenant_id;
   "
   ```

### 5. Recovering from a Failed Run

**Diagnosis steps**:
```bash
# 1. Get run details
curl "https://your-api-url.com/api/v1/runs/FAILED_RUN_ID"

# 2. Check validation errors
psql $SUPABASE_URL -c "
SELECT * FROM validation_errors 
WHERE run_id = 'FAILED_RUN_ID' 
ORDER BY created_at;
"

# 3. Check system logs
# In Render/Fly dashboard, view application logs around the failure time

# 4. Check database state
psql $SUPABASE_URL -c "
SELECT status, error_message, validation_errors_count 
FROM cogs_runs 
WHERE run_id = 'FAILED_RUN_ID';
"
```

**Recovery options**:

**Option A: Fix data and re-run**
```bash
# 1. Identify data issues from validation errors
# 2. Clean up any partial data (if run failed mid-process)
python -m app.cli rollback FAILED_RUN_ID --confirm

# 3. Fix source data
# 4. Re-run with corrected data
python -m app.cli run --tenant-id "tenant" --sales-file corrected_sales.csv
```

**Option B: Restore from backup**
```bash
# If run caused data corruption, restore from backup
# See docs/BACKUP_RECOVERY.md for detailed steps
```

### 6. Generating Journal Entries

**For accounting integration (Xero, QuickBooks, etc.)**:

```bash
# Generate CSV format
python -m app.cli journal-entry RUN_123456 \
  --format csv \
  --output-file journal_entries.csv

# Generate JSON format
curl "https://your-api-url.com/api/v1/runs/RUN_123456/journal-entry?format=json" \
  > journal_entries.json

# Generate QuickBooks IIF format (if implemented)
python -m app.cli journal-entry RUN_123456 \
  --format iif \
  --output-file quickbooks_import.iif
```

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. "Concurrent run detected" Error (409)

**Symptoms**: Cannot start new COGS run, API returns 409 error
**Cause**: Another run is already in progress for the same tenant

**Solution**:
```bash
# Check for active runs
curl "https://your-api-url.com/api/v1/runs?tenant_id=affected-tenant&status=running"

# If stuck run found, investigate logs and consider manual cleanup
psql $SUPABASE_URL -c "
UPDATE cogs_runs 
SET status = 'failed', 
    error_message = 'Manually marked as failed - stuck process',
    updated_at = NOW()
WHERE run_id = 'STUCK_RUN_ID' AND status = 'running';
"
```

#### 2. Dashboard Login Issues

**Symptoms**: Users cannot login, authentication errors
**Cause**: Supabase auth issues, expired keys, RLS problems

**Diagnosis**:
```bash
# Check Supabase auth status
curl -X POST https://your-project.supabase.co/auth/v1/signup \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

**Solutions**:
- Check SUPABASE_ANON_KEY is not expired
- Verify RLS policies are not blocking user access
- Clear browser localStorage and cookies

#### 3. File Upload Failures

**Symptoms**: CSV uploads fail, validation errors
**Cause**: Incorrect file format, missing columns, data type issues

**Diagnosis**:
```bash
# Check file format matches template
curl -X GET https://your-api-url.com/api/v1/files/templates/sales

# Validate CSV manually
python -c "
import pandas as pd
df = pd.read_csv('problematic_file.csv')
print('Columns:', df.columns.tolist())
print('Shape:', df.shape)
print('First few rows:')
print(df.head())
"
```

**Solutions**:
- Download fresh templates
- Check for BOM characters: `od -c file.csv | head`
- Validate date formats match ISO 8601
- Ensure no missing required columns

#### 4. High Memory Usage / Slow Performance

**Symptoms**: API timeouts, out of memory errors, slow COGS calculations
**Cause**: Large datasets, inefficient queries, memory leaks

**Diagnosis**:
```bash
# Check system resources
curl https://your-api-url.com/metrics | grep memory

# Check database performance
psql $SUPABASE_URL -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

**Solutions**:
- Process data in smaller batches
- Add database indexes if missing
- Increase API server memory allocation
- Consider pagination for large result sets

#### 5. Rollback Failures

**Symptoms**: Rollback operation fails, incomplete rollback
**Cause**: Missing snapshots, concurrent operations, data integrity issues

**Diagnosis**:
```bash
# Check if snapshots exist
psql $SUPABASE_URL -c "
SELECT * FROM inventory_snapshots 
WHERE run_id = 'PROBLEMATIC_RUN_ID';
"

# Check run status
psql $SUPABASE_URL -c "
SELECT * FROM cogs_runs 
WHERE run_id = 'PROBLEMATIC_RUN_ID';
"
```

**Solutions**:
- Ensure no concurrent operations during rollback
- Check snapshot integrity
- Manual rollback using SQL if automated rollback fails

## Incident Response

### Severity Levels

**P0 - Critical (Response: Immediate)**
- System completely down
- Data corruption detected
- Security breach

**P1 - High (Response: 1 hour)**
- Single tenant unable to operate
- Significant performance degradation
- Backup system failures

**P2 - Medium (Response: 4 hours)**
- Minor feature issues
- Performance issues affecting some operations

**P3 - Low (Response: 24 hours)**
- Cosmetic issues
- Enhancement requests

### Incident Response Steps

1. **Incident Detection**:
   ```bash
   # Immediate health check
   ./scripts/daily_health_check.sh
   
   # Check error rates
   curl https://your-api-url.com/metrics | grep error_rate
   ```

2. **Impact Assessment**:
   - How many tenants affected?
   - What operations are failing?
   - Is data at risk?

3. **Communication**:
   ```bash
   # Notify stakeholders
   curl -X POST $SLACK_WEBHOOK_URL \
     -H 'Content-type: application/json' \
     --data '{"text":"🚨 FIFO COGS Incident: [Brief Description]"}'
   ```

4. **Mitigation**:
   - Apply temporary fixes
   - Scale resources if needed
   - Redirect traffic if necessary

5. **Resolution**:
   - Implement permanent fix
   - Verify system stability
   - Update documentation

6. **Post-Incident Review**:
   - Document timeline
   - Identify root cause
   - Create prevention measures

## Monitoring & Alerting

### Key Metrics to Monitor

```bash
# Error rate threshold: >5% in 15 minutes
curl https://your-api-url.com/metrics | grep http_requests_total

# Response time threshold: >2 seconds average
curl https://your-api-url.com/metrics | grep http_request_duration

# Failed runs threshold: >3 in 1 hour
psql $SUPABASE_URL -c "
SELECT COUNT(*) FROM cogs_runs 
WHERE status = 'failed' 
AND created_at >= NOW() - INTERVAL '1 hour';
"

# Database connections threshold: >80% of max
psql $SUPABASE_URL -c "
SELECT numbackends, setting as max_connections 
FROM pg_stat_database, pg_settings 
WHERE datname = current_database() 
AND name = 'max_connections';
"
```

### Alert Configuration

Set up alerts for:
- API health check failures (>2 consecutive failures)
- Dashboard unavailability (>5 minutes)
- Database connection failures
- High error rates (>5% in 15 minutes)
- Failed runs spike (>3 in 1 hour)
- Disk space (>80% full)
- Memory usage (>85%)

## Maintenance Windows

### Scheduled Maintenance (Monthly)

```bash
#!/bin/bash
# monthly_maintenance.sh

echo "🔧 Starting monthly maintenance - $(date)"

# 1. Update dependencies
echo "📦 Checking for updates..."
# (This would trigger deployment pipeline with updated dependencies)

# 2. Database maintenance
echo "🗄️  Database maintenance..."
psql $SUPABASE_URL << EOF
-- Analyze tables for query optimization
ANALYZE;

-- Reindex if needed
REINDEX DATABASE current_database();

-- Clean up old data (if applicable)
DELETE FROM validation_errors 
WHERE created_at < NOW() - INTERVAL '6 months';
EOF

# 3. Backup verification
echo "💾 Verifying backups..."
./scripts/backup_health_check.sh

# 4. Security updates
echo "🔐 Security check..."
./scripts/check_key_expiry.sh

echo "✅ Monthly maintenance complete"
```

### Emergency Maintenance

For urgent fixes:
1. **Announce maintenance** (15 minutes notice minimum)
2. **Enable maintenance mode** (if available)
3. **Perform fix**
4. **Verify system health**
5. **Disable maintenance mode**
6. **Announce completion**

## Contact Information

### Escalation Matrix

**Level 1: System Administrator**
- Primary on-call rotation
- Handles routine operations
- Escalates if unable to resolve in 30 minutes

**Level 2: Lead Developer**
- Code-related issues
- Complex troubleshooting
- Escalates to vendor support if needed

**Level 3: Vendor Support**
- Supabase Support (Pro+ plans)
- Render/Vercel Support (Paid plans)
- Infrastructure provider support

### Emergency Contacts

```
On-Call Engineer: [Phone/Slack]
Lead Developer: [Phone/Email]
System Administrator: [Phone/Email]
Business Owner: [Email]

Vendor Support:
- Supabase: support@supabase.io
- Render: support@render.com
- Vercel: support@vercel.com
```

---

**Last Updated**: $(date +"%Y-%m-%d")
**Next Review Date**: $(date -d "+3 months" +"%Y-%m-%d")