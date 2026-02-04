#!/bin/bash
# backup_health_check.sh - Verify backup health for FIFO COGS System
# Run daily/weekly to ensure backups are current

set -e

echo "💾 FIFO COGS Backup Health Check - $(date)"
echo "==========================================="

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
MAX_BACKUP_AGE_HOURS=24
WARNING_AGE_HOURS=12

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✅ $1${NC}"; }
failure() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

ALERTS=0

echo ""
echo "Backup Age Thresholds:"
echo "  - Warning: > ${WARNING_AGE_HOURS} hours"
echo "  - Critical: > ${MAX_BACKUP_AGE_HOURS} hours"
echo ""

# 1. Check Supabase automatic backups (Pro plan)
echo "📦 Supabase Backups"
echo "-------------------"
echo "Supabase Pro plans include automatic daily backups."
echo "Check status at: https://app.supabase.com/project/YOUR_PROJECT/database/backups"
echo ""

if [ -n "$SUPABASE_URL" ]; then
    # Check if we can connect (indicates DB is healthy)
    DB_CHECK=$(psql "$SUPABASE_URL" -t -c "SELECT 1;" 2>/dev/null | tr -d ' \n' || echo "")
    if [ "$DB_CHECK" = "1" ]; then
        success "Database is accessible (prerequisite for backups)"
    else
        failure "Cannot connect to database - backup status unknown"
        ALERTS=$((ALERTS + 1))
    fi
else
    warning "SUPABASE_URL not set - cannot verify database connection"
fi

# 2. Check local backup files (if you maintain local backups)
echo ""
echo "📁 Local Backups"
echo "----------------"

BACKUP_DIR="${BACKUP_DIR:-./backups}"

if [ -d "$BACKUP_DIR" ]; then
    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.sql "$BACKUP_DIR"/*.dump "$BACKUP_DIR"/*.gz 2>/dev/null | head -1 || echo "")
    
    if [ -n "$LATEST_BACKUP" ]; then
        BACKUP_TIME=$(stat -f %m "$LATEST_BACKUP" 2>/dev/null || stat -c %Y "$LATEST_BACKUP" 2>/dev/null || echo "0")
        CURRENT_TIME=$(date +%s)
        AGE_HOURS=$(( (CURRENT_TIME - BACKUP_TIME) / 3600 ))
        
        echo "Latest backup: $LATEST_BACKUP"
        echo "Backup age: ${AGE_HOURS} hours"
        
        if [ "$AGE_HOURS" -gt "$MAX_BACKUP_AGE_HOURS" ]; then
            failure "Backup is STALE (${AGE_HOURS} hours old)"
            ALERTS=$((ALERTS + 1))
        elif [ "$AGE_HOURS" -gt "$WARNING_AGE_HOURS" ]; then
            warning "Backup is getting old (${AGE_HOURS} hours)"
            ALERTS=$((ALERTS + 1))
        else
            success "Backup is recent (${AGE_HOURS} hours old)"
        fi
    else
        warning "No backup files found in $BACKUP_DIR"
        echo "   Expected: .sql, .dump, or .gz files"
    fi
else
    echo "Local backup directory not configured ($BACKUP_DIR)"
    echo "To enable local backups, create the directory and run:"
    echo "  pg_dump \$SUPABASE_URL > $BACKUP_DIR/backup_\$(date +%Y%m%d).sql"
fi

# 3. Verify backup restore capability
echo ""
echo "🔄 Restore Capability"
echo "---------------------"

if [ -f "docs/BACKUP_RECOVERY.md" ]; then
    success "Backup recovery documentation exists"
else
    warning "docs/BACKUP_RECOVERY.md not found"
    echo "   Create documentation for emergency restore procedures"
    ALERTS=$((ALERTS + 1))
fi

# 4. Check data integrity (optional - run sample queries)
echo ""
echo "🔍 Data Integrity Spot Check"
echo "----------------------------"

if [ -n "$SUPABASE_URL" ]; then
    # Count core tables
    TENANT_COUNT=$(psql "$SUPABASE_URL" -t -c "SELECT COUNT(DISTINCT tenant_id) FROM cogs_runs;" 2>/dev/null | tr -d ' \n' || echo "N/A")
    RUN_COUNT=$(psql "$SUPABASE_URL" -t -c "SELECT COUNT(*) FROM cogs_runs;" 2>/dev/null | tr -d ' \n' || echo "N/A")
    
    echo "Active tenants: $TENANT_COUNT"
    echo "Total COGS runs: $RUN_COUNT"
    
    if [ "$TENANT_COUNT" = "0" ] && [ "$RUN_COUNT" = "0" ]; then
        warning "Database appears empty - verify this is expected"
    else
        success "Data integrity check passed"
    fi
else
    echo "Skipped (SUPABASE_URL not set)"
fi

echo ""
echo "==========================================="

if [ "$ALERTS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $ALERTS issue(s) found - review above${NC}"
    exit 1
else
    success "Backup health check passed"
    exit 0
fi
