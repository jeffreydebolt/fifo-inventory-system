#!/bin/bash
# weekly_metrics.sh - FIFO COGS System Weekly Metrics Report
# Run weekly to track system usage and performance

set -e

echo "📊 FIFO COGS Weekly Metrics Report - $(date)"
echo "=============================================="

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$SUPABASE_URL" ]; then
    echo "❌ SUPABASE_URL not set. Cannot generate metrics."
    echo "   Set SUPABASE_URL in .env or environment"
    exit 1
fi

echo ""
echo "📈 Activity Metrics (Last 7 Days)"
echo "-----------------------------------"

psql "$SUPABASE_URL" -t << 'EOF'
SELECT 'Active Tenants' as metric, COUNT(DISTINCT tenant_id)::text as value
FROM cogs_runs 
WHERE created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 'Total Runs', COUNT(*)::text
FROM cogs_runs 
WHERE created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 'Successful Runs', COUNT(*)::text
FROM cogs_runs 
WHERE status = 'completed' AND created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 'Failed Runs', COUNT(*)::text
FROM cogs_runs 
WHERE status = 'failed' AND created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 'Rollbacks', COUNT(*)::text
FROM cogs_runs 
WHERE status = 'rolled_back' AND created_at >= NOW() - INTERVAL '7 days';
EOF

echo ""
echo "📉 Failure Analysis"
echo "-------------------"

psql "$SUPABASE_URL" << 'EOF'
SELECT 
    COALESCE(error_message, 'Unknown') as error_type,
    COUNT(*) as occurrences
FROM cogs_runs 
WHERE status = 'failed' 
AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY error_message
ORDER BY occurrences DESC
LIMIT 5;
EOF

echo ""
echo "🏆 Top Active Tenants"
echo "---------------------"

psql "$SUPABASE_URL" << 'EOF'
SELECT 
    tenant_id,
    COUNT(*) as runs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM cogs_runs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY tenant_id
ORDER BY runs DESC
LIMIT 10;
EOF

echo ""
echo "💾 Database Size"
echo "----------------"

psql "$SUPABASE_URL" << 'EOF'
SELECT 
    tablename as table_name,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size('public.' || tablename) DESC
LIMIT 10;
EOF

echo ""
echo "⏱️  Processing Times (Last 7 Days)"
echo "-----------------------------------"

psql "$SUPABASE_URL" << 'EOF'
SELECT 
    'Average' as metric,
    ROUND(AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))::numeric, 2)::text || 's' as duration
FROM cogs_runs 
WHERE status = 'completed' 
AND created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
    'Max',
    ROUND(MAX(EXTRACT(EPOCH FROM (updated_at - created_at)))::numeric, 2)::text || 's'
FROM cogs_runs 
WHERE status = 'completed' 
AND created_at >= NOW() - INTERVAL '7 days'
UNION ALL
SELECT 
    'Min',
    ROUND(MIN(EXTRACT(EPOCH FROM (updated_at - created_at)))::numeric, 2)::text || 's'
FROM cogs_runs 
WHERE status = 'completed' 
AND created_at >= NOW() - INTERVAL '7 days';
EOF

echo ""
echo "=============================================="
echo "Weekly metrics report complete - $(date)"
