# Next Steps for Completing Step 5: CI/CD, Monitoring, and Ops Runbook

## Current Status
Step 5 is approximately 85% complete. The following components have been created but need to be organized and committed:

### ✅ Already Created:
1. `.github/workflows/api-ci.yml` - API CI/CD pipeline
2. `.github/workflows/dashboard-ci.yml` - Dashboard CI/CD pipeline  
3. `Dockerfile` - For API containerization
4. `requirements.txt` - Python dependencies
5. `api/app.py` - Updated with Sentry and Prometheus monitoring
6. `cogs-dashboard/package.json` - Updated with Sentry dependency
7. `cogs-dashboard/src/index.js` - Updated with Sentry initialization
8. `docs/BACKUP_RECOVERY.md` - Comprehensive backup procedures
9. `docs/SECRETS_ROTATION.md` - Complete secrets management guide
10. `README_OPS.md` - Full operations runbook
11. `scripts/rollback_and_rerun.sh` - Rollback/rerun support macro

## Remaining Micro-Steps

### 1. Create Missing Support Scripts
**Files to create:**
- `scripts/daily_health_check.sh` - Daily system health checks
- `scripts/weekly_metrics.sh` - Weekly metrics collection
- `scripts/emergency_key_rotation.sh` - Emergency key rotation
- `scripts/check_key_expiry.sh` - Key expiration monitoring
- `scripts/backup_health_check.sh` - Backup verification
- `scripts/csv_validation_response.sh` - CSV error helper

### 2. Create Support Macros Documentation
**File to create:**
- `docs/SUPPORT_MACROS.md` - Documentation for all support scripts

### 3. Make Scripts Executable
**Command to run:**
```bash
chmod +x scripts/*.sh
```

### 4. Commit Current WIP
**Commands:**
```bash
git add -A
git commit -m "WIP: Step 5 - CI/CD, monitoring, and ops infrastructure (partial)

- GitHub Actions workflows for API and dashboard
- Sentry integration started
- Backup and secrets documentation
- Operations runbook
- First support macro (rollback_and_rerun.sh)

Work in progress - additional scripts pending"
git push
```

### 5. Complete Remaining Scripts and Final Commit
**After creating remaining scripts, final commit:**
```bash
git add scripts/
git add docs/SUPPORT_MACROS.md
git commit -m "feat: Complete Step 5 - CI/CD, monitoring, and ops infrastructure

- Add remaining support macros for operations
- Daily health check and weekly metrics scripts  
- Emergency key rotation and expiry monitoring
- CSV validation error response helper
- Comprehensive support macros documentation
- Make all scripts executable

Completes Step 5 deliverables:
✅ GitHub Actions CI/CD pipelines
✅ Deploy pipelines with tag/merge triggers
✅ Sentry monitoring integration
✅ Prometheus metrics for API
✅ Backup and recovery procedures
✅ Secrets rotation guide and scripts
✅ Operations runbook with troubleshooting
✅ Support macros for common operations

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

## Script Contents Preview

### `scripts/daily_health_check.sh`
- Check API health endpoint
- Check dashboard availability
- Verify database connectivity
- Check recent activity (runs in last 24h)
- Monitor error rates
- Output formatted report

### `scripts/weekly_metrics.sh`
- Count active tenants (7 days)
- Total runs and rollbacks
- Failed runs analysis
- Database size by table
- Performance metrics summary

### `scripts/emergency_key_rotation.sh`
- Interactive script for urgent key rotation
- Updates all deployment platforms
- Tests new keys immediately
- Provides rollback instructions

### `scripts/check_key_expiry.sh`
- Reads last rotation dates
- Alerts if keys are overdue
- Integrates with monitoring/alerting

### `scripts/backup_health_check.sh`
- Verifies latest backup timestamp
- Checks backup age
- Alerts if backups are stale

### `scripts/csv_validation_response.sh`
- Parses CSV validation errors
- Provides user-friendly error messages
- Suggests fixes for common issues
- Generates example valid CSV

## Time Estimate
- Creating remaining scripts: 15-20 minutes
- Documentation: 5-10 minutes
- Testing and commits: 5 minutes
- **Total: ~30 minutes to complete Step 5**

## Notes
- All scripts should include proper error handling
- Scripts should be idempotent where possible
- Include usage/help information in each script
- Test scripts locally before committing
- Ensure scripts work with both local and production environments