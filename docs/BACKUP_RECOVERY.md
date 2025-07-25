# Backup & Recovery Guide

## Overview

The FIFO COGS system uses Supabase (PostgreSQL) as the primary database. This guide covers backup strategies, automated procedures, and step-by-step recovery processes.

## Automated Backups

### Supabase Built-in Backups

Supabase automatically creates:
- **Point-in-time recovery**: Up to 7 days for Free tier, 30 days for Pro+
- **Daily snapshots**: Retained based on your plan
- **WAL (Write-Ahead Log)**: For continuous backup

### Backup Schedule
```
Daily:     02:00 UTC - Full database snapshot
Hourly:    WAL segments (continuous)
Weekly:    Long-term retention snapshot (Pro+ only)
```

### Accessing Backups

1. **Supabase Dashboard**:
   - Go to Settings → Database
   - Click "Backups" tab
   - View available snapshots and PITR options

2. **CLI Access**:
   ```bash
   supabase db dump --db-url $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

## Data Retention Policy

### Production Data
- **COGS Runs**: Retained indefinitely (audit requirement)
- **Inventory Snapshots**: Retained for 2 years minimum
- **Inventory Movements**: Retained indefinitely (compliance)
- **Validation Errors**: Retained for 1 year

### Cleanup Scripts
```sql
-- Clean old validation errors (>1 year)
DELETE FROM validation_errors 
WHERE created_at < NOW() - INTERVAL '1 year';

-- Archive old inventory snapshots (>2 years)
CREATE TABLE inventory_snapshots_archive AS 
SELECT * FROM inventory_snapshots 
WHERE created_at < NOW() - INTERVAL '2 years';

DELETE FROM inventory_snapshots 
WHERE created_at < NOW() - INTERVAL '2 years';
```

## Recovery Procedures

### 1. Point-in-Time Recovery (PITR)

**When to use**: Data corruption, accidental deletion within last 7-30 days

**Steps**:
1. **Identify target recovery time**:
   ```bash
   # Check when the issue occurred
   psql $DATABASE_URL -c "SELECT * FROM cogs_runs WHERE created_at > '2024-07-20 10:00:00' ORDER BY created_at;"
   ```

2. **Create recovery database**:
   - Go to Supabase Dashboard → Settings → Database
   - Click "Point in time recovery"
   - Select target timestamp
   - Choose "Create new project" (recommended)

3. **Verify recovered data**:
   ```bash
   # Connect to recovery database
   psql $RECOVERY_DATABASE_URL
   
   # Verify critical data
   SELECT COUNT(*) FROM cogs_runs;
   SELECT COUNT(*) FROM inventory_movements;
   SELECT MAX(created_at) FROM cogs_runs;
   ```

4. **Switch traffic** (if recovery is good):
   - Update `SUPABASE_URL` in API deployment
   - Update connection strings in dashboard
   - Test end-to-end functionality

### 2. Full Database Restore

**When to use**: Complete data loss, major corruption

**Steps**:
1. **Create new Supabase project**:
   ```bash
   # Create project via CLI or dashboard
   supabase projects create fifo-cogs-recovery
   ```

2. **Restore from SQL dump**:
   ```bash
   # Get latest backup
   supabase db dump --db-url $OLD_DATABASE_URL > latest_backup.sql
   
   # Restore to new project
   psql $NEW_DATABASE_URL < latest_backup.sql
   ```

3. **Run migrations** (if needed):
   ```bash
   psql $NEW_DATABASE_URL -f infra/migrations/001_create_multi_tenant_schema.sql
   ```

4. **Verify data integrity**:
   ```bash
   # Run verification queries
   psql $NEW_DATABASE_URL << EOF
   SELECT 
     COUNT(*) as total_runs,
     COUNT(DISTINCT tenant_id) as unique_tenants,
     MAX(created_at) as last_run
   FROM cogs_runs;
   
   SELECT 
     tenant_id,
     COUNT(*) as run_count,
     MAX(created_at) as last_run
   FROM cogs_runs 
   GROUP BY tenant_id;
   EOF
   ```

### 3. Partial Data Recovery

**When to use**: Specific tenant data loss, corrupted run data

**Steps**:
1. **Identify affected scope**:
   ```sql
   -- Find missing or corrupted data
   SELECT * FROM cogs_runs 
   WHERE tenant_id = 'affected-tenant' 
   AND created_at BETWEEN '2024-07-20' AND '2024-07-21';
   ```

2. **Extract from backup**:
   ```bash
   # Dump specific tenant data from backup
   pg_dump $BACKUP_DATABASE_URL \
     --data-only \
     --table=cogs_runs \
     --table=inventory_movements \
     --table=inventory_snapshots \
     --where="tenant_id='affected-tenant'" \
     > tenant_recovery.sql
   ```

3. **Restore selectively**:
   ```bash
   # Remove conflicting data first
   psql $PRODUCTION_DATABASE_URL << EOF
   DELETE FROM inventory_snapshots 
   WHERE tenant_id = 'affected-tenant' 
   AND created_at BETWEEN 'start_time' AND 'end_time';
   
   DELETE FROM inventory_movements 
   WHERE tenant_id = 'affected-tenant' 
   AND created_at BETWEEN 'start_time' AND 'end_time';
   
   DELETE FROM cogs_runs 
   WHERE tenant_id = 'affected-tenant' 
   AND created_at BETWEEN 'start_time' AND 'end_time';
   EOF
   
   # Restore from backup
   psql $PRODUCTION_DATABASE_URL < tenant_recovery.sql
   ```

## Recovery Testing

### Monthly Recovery Drills

1. **Test PITR process**:
   ```bash
   #!/bin/bash
   # recovery_drill.sh
   
   echo "Starting recovery drill..."
   
   # Create test data
   curl -X POST $API_URL/api/v1/runs \
     -H "Content-Type: application/json" \
     -d '{"tenant_id": "recovery-test", "mode": "fifo", "sales_data": [], "lots_data": []}'
   
   # Note timestamp
   RECOVERY_TIME=$(date -u +"%Y-%m-%d %H:%M:%S")
   echo "Recovery target: $RECOVERY_TIME"
   
   # Simulate data loss (delete test data)
   psql $DATABASE_URL -c "DELETE FROM cogs_runs WHERE tenant_id = 'recovery-test';"
   
   # Verify deletion
   DELETED_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM cogs_runs WHERE tenant_id = 'recovery-test';")
   echo "Deleted records: $DELETED_COUNT"
   
   # Perform PITR recovery (manual step)
   echo "Perform PITR recovery in Supabase Dashboard to timestamp: $RECOVERY_TIME"
   echo "Then run: ./verify_recovery.sh"
   ```

2. **Verify recovery**:
   ```bash
   #!/bin/bash
   # verify_recovery.sh
   
   RECOVERED_COUNT=$(psql $RECOVERY_DATABASE_URL -t -c "SELECT COUNT(*) FROM cogs_runs WHERE tenant_id = 'recovery-test';")
   
   if [ "$RECOVERED_COUNT" -gt 0 ]; then
     echo "✅ Recovery successful: $RECOVERED_COUNT records recovered"
   else
     echo "❌ Recovery failed: No records found"
     exit 1
   fi
   ```

## Backup Monitoring

### Health Checks

Add to monitoring system:
```bash
#!/bin/bash
# backup_health_check.sh

# Check last backup timestamp
LAST_BACKUP=$(psql $DATABASE_URL -t -c "SELECT pg_last_wal_replay_lsn();")

# Check backup age
BACKUP_AGE_HOURS=$(psql $DATABASE_URL -t -c "
  SELECT EXTRACT(EPOCH FROM (NOW() - pg_stat_file('base/backup_label')::timestamp)) / 3600;
")

if [ "$BACKUP_AGE_HOURS" -gt 25 ]; then
  echo "❌ Backup is $BACKUP_AGE_HOURS hours old - investigation required"
  exit 1
else
  echo "✅ Backup is current ($BACKUP_AGE_HOURS hours old)"
fi
```

### Alerts

Set up alerts for:
- Backup failures (>24 hours without backup)
- WAL segment delays (>1 hour)
- Disk space warnings (>80% full)
- Recovery drill failures

## Emergency Contacts

### Escalation Path
1. **Level 1**: System Administrator
2. **Level 2**: Database Team Lead  
3. **Level 3**: Supabase Support (Pro+ plans)

### Communication Plan
- **Incident declared**: Notify stakeholders within 15 minutes
- **Status updates**: Every 30 minutes during recovery
- **Resolution**: Full post-mortem within 48 hours

## Recovery Validation Checklist

After any recovery procedure:

- [ ] **Data Completeness**: All expected tables and records present
- [ ] **Referential Integrity**: Foreign key constraints satisfied
- [ ] **Tenant Isolation**: RLS policies working correctly
- [ ] **Application Connectivity**: API can connect and query
- [ ] **Dashboard Functionality**: UI loads and displays data
- [ ] **Run Creation**: Can create new COGS runs
- [ ] **Rollback Functionality**: Can rollback recent runs
- [ ] **File Uploads**: Can upload lots and sales files
- [ ] **Journal Exports**: Can generate journal entries
- [ ] **Multi-tenant**: Each tenant sees only their data

## Documentation Updates

Keep this document updated when:
- Backup procedures change
- New recovery scenarios are discovered
- Contact information changes
- Recovery validation steps are modified

Last updated: $(date +"%Y-%m-%d")