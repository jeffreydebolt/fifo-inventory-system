#!/bin/bash
# check_key_expiry.sh - Check for keys/secrets approaching expiration
# Run weekly to ensure credentials are rotated before expiry

set -e

echo "🔑 FIFO COGS Key Expiry Check - $(date)"
echo "========================================"

# Configuration - adjust these values
ROTATION_POLICY_DAYS=90
WARNING_THRESHOLD_DAYS=14

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SECRETS_FILE="docs/SECRETS_ROTATION.md"
ALERTS=0

check_key() {
    local key_name="$1"
    local last_rotation="$2"
    
    if [ -z "$last_rotation" ] || [ "$last_rotation" = "N/A" ]; then
        echo -e "${YELLOW}⚠️  $key_name: No rotation date recorded${NC}"
        ALERTS=$((ALERTS + 1))
        return
    fi
    
    # Calculate days since rotation
    last_epoch=$(date -j -f "%Y-%m-%d" "$last_rotation" +%s 2>/dev/null || date -d "$last_rotation" +%s 2>/dev/null || echo "0")
    current_epoch=$(date +%s)
    days_since=$(( (current_epoch - last_epoch) / 86400 ))
    days_until_expiry=$(( ROTATION_POLICY_DAYS - days_since ))
    
    if [ "$days_until_expiry" -le 0 ]; then
        echo -e "${RED}❌ $key_name: OVERDUE for rotation (${days_since} days old)${NC}"
        ALERTS=$((ALERTS + 1))
    elif [ "$days_until_expiry" -le "$WARNING_THRESHOLD_DAYS" ]; then
        echo -e "${YELLOW}⚠️  $key_name: Rotation due in ${days_until_expiry} days (last: $last_rotation)${NC}"
        ALERTS=$((ALERTS + 1))
    else
        echo -e "${GREEN}✅ $key_name: OK (${days_until_expiry} days until rotation due)${NC}"
    fi
}

echo ""
echo "Rotation Policy: Every $ROTATION_POLICY_DAYS days"
echo "Warning Threshold: $WARNING_THRESHOLD_DAYS days before expiry"
echo ""

# Check if secrets rotation file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "${YELLOW}⚠️  $SECRETS_FILE not found${NC}"
    echo "Creating template..."
    
    mkdir -p docs
    cat > "$SECRETS_FILE" << 'EOF'
# Secrets Rotation Log

## Rotation Policy
- All secrets should be rotated every 90 days
- Emergency rotations should be logged immediately
- Never commit secrets to version control

## Rotation History

| Date | Secret | Reason | Rotated By |
|------|--------|--------|------------|
| YYYY-MM-DD | Supabase Service Key | Initial setup | Your Name |
| YYYY-MM-DD | Sentry DSN | Initial setup | Your Name |

## Last Rotation Dates

- **Supabase Service Key**: YYYY-MM-DD
- **Supabase Anon Key**: YYYY-MM-DD
- **Sentry DSN (API)**: YYYY-MM-DD
- **Sentry DSN (Dashboard)**: YYYY-MM-DD

## Emergency Rotation Procedure

See `scripts/emergency_key_rotation.sh`
EOF
    
    echo "Template created at $SECRETS_FILE"
    echo "Please update with actual rotation dates"
    exit 1
fi

# Parse last rotation dates from the file
echo "Checking secrets rotation status..."
echo ""

# Try to extract dates from the file
SUPABASE_SERVICE_DATE=$(grep -i "Supabase Service Key" "$SECRETS_FILE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1 || echo "N/A")
SUPABASE_ANON_DATE=$(grep -i "Supabase Anon Key" "$SECRETS_FILE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1 || echo "N/A")
SENTRY_API_DATE=$(grep -i "Sentry DSN (API)" "$SECRETS_FILE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1 || echo "N/A")
SENTRY_DASHBOARD_DATE=$(grep -i "Sentry DSN (Dashboard)" "$SECRETS_FILE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tail -1 || echo "N/A")

check_key "Supabase Service Key" "$SUPABASE_SERVICE_DATE"
check_key "Supabase Anon Key" "$SUPABASE_ANON_DATE"
check_key "Sentry DSN (API)" "$SENTRY_API_DATE"
check_key "Sentry DSN (Dashboard)" "$SENTRY_DASHBOARD_DATE"

echo ""
echo "========================================"

if [ "$ALERTS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $ALERTS key(s) need attention${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All keys within rotation policy${NC}"
    exit 0
fi
