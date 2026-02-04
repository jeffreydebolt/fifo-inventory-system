#!/bin/bash
# daily_health_check.sh - FIFO COGS System Daily Health Check
# Run this daily to verify system health

set -e

echo "🏥 FIFO COGS System Health Check - $(date)"
echo "================================================"

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
API_URL="${FIFO_API_URL:-https://fifo-cogs-api.onrender.com}"
DASHBOARD_URL="${FIFO_DASHBOARD_URL:-https://fifo-cogs-dashboard.vercel.app}"
TIMEOUT=10

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✅ $1${NC}"; }
failure() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# 1. API Health
echo ""
echo "🔍 Checking API health..."
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$API_URL/healthz" 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    API_RESPONSE=$(curl -s --max-time $TIMEOUT "$API_URL/healthz" 2>/dev/null || echo "{}")
    success "API is healthy (HTTP $API_STATUS)"
    echo "   Response: $API_RESPONSE"
elif [ "$API_STATUS" = "000" ]; then
    failure "API is unreachable (timeout or connection refused)"
else
    failure "API returned HTTP $API_STATUS"
fi

# 2. Dashboard Health
echo ""
echo "🔍 Checking dashboard health..."
DASHBOARD_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$DASHBOARD_URL" 2>/dev/null || echo "000")

if [ "$DASHBOARD_STATUS" = "200" ]; then
    success "Dashboard is healthy (HTTP $DASHBOARD_STATUS)"
elif [ "$DASHBOARD_STATUS" = "000" ]; then
    failure "Dashboard is unreachable"
else
    warning "Dashboard returned HTTP $DASHBOARD_STATUS"
fi

# 3. Database Connectivity (if SUPABASE_URL is set)
echo ""
echo "🔍 Checking database connectivity..."
if [ -n "$SUPABASE_URL" ]; then
    DB_CHECK=$(psql "$SUPABASE_URL" -t -c "SELECT 1;" 2>/dev/null | tr -d ' \n' || echo "")
    if [ "$DB_CHECK" = "1" ]; then
        success "Database is accessible"
    else
        failure "Database connection failed"
    fi
else
    warning "SUPABASE_URL not set - skipping database check"
fi

# 4. Recent Activity (if database accessible)
if [ -n "$SUPABASE_URL" ]; then
    echo ""
    echo "📊 Recent activity (last 24 hours)..."
    
    RECENT_RUNS=$(psql "$SUPABASE_URL" -t -c "SELECT COUNT(*) FROM cogs_runs WHERE created_at >= NOW() - INTERVAL '24 hours';" 2>/dev/null | tr -d ' \n' || echo "N/A")
    echo "   COGS runs: $RECENT_RUNS"
    
    FAILED_RUNS=$(psql "$SUPABASE_URL" -t -c "SELECT COUNT(*) FROM cogs_runs WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '24 hours';" 2>/dev/null | tr -d ' \n' || echo "N/A")
    echo "   Failed runs: $FAILED_RUNS"
    
    if [ "$FAILED_RUNS" != "N/A" ] && [ "$FAILED_RUNS" -gt 5 ]; then
        warning "High failure rate detected - investigation recommended"
    fi
    
    ROLLBACKS=$(psql "$SUPABASE_URL" -t -c "SELECT COUNT(*) FROM cogs_runs WHERE status = 'rolled_back' AND created_at >= NOW() - INTERVAL '24 hours';" 2>/dev/null | tr -d ' \n' || echo "N/A")
    echo "   Rollbacks: $ROLLBACKS"
fi

echo ""
echo "================================================"
echo "Health check complete - $(date)"
