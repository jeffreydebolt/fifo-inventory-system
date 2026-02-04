#!/bin/bash
# emergency_key_rotation.sh - Emergency Key Rotation for FIFO COGS System
# Use this when keys are compromised or need immediate rotation

set -e

echo "🔐 FIFO COGS Emergency Key Rotation"
echo "===================================="
echo ""
echo "⚠️  This script guides you through emergency key rotation."
echo "    Follow each step carefully."
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}━━━ Step $1: $2 ━━━${NC}"; }
action() { echo -e "${YELLOW}→ $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

ROTATION_LOG="key_rotation_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to: $ROTATION_LOG"

{
    echo "Key Rotation Started: $(date)"
    echo "Reason: Emergency rotation"
    echo ""
} >> "$ROTATION_LOG"

step 1 "Generate New Supabase Service Key"
action "Go to: https://app.supabase.com/project/YOUR_PROJECT/settings/api"
action "Click 'Generate new key' under Service Role Key"
echo ""
read -p "Press Enter when new Supabase key is generated..."
echo "Supabase key rotated: $(date)" >> "$ROTATION_LOG"

step 2 "Update API Server (Render/Fly)"
action "Go to your API deployment dashboard"
action "Update SUPABASE_SERVICE_ROLE_KEY with the new key"
action "Trigger a redeploy"
echo ""
echo "For Render:"
echo "  1. Dashboard → Environment → Edit SUPABASE_SERVICE_ROLE_KEY"
echo "  2. Save and deploy"
echo ""
echo "For Fly.io:"
echo "  fly secrets set SUPABASE_SERVICE_ROLE_KEY='new_key_here'"
echo ""
read -p "Press Enter when API is updated and redeployed..."
echo "API updated: $(date)" >> "$ROTATION_LOG"

step 3 "Verify API Health"
action "Testing API health endpoint..."

API_URL="${FIFO_API_URL:-https://fifo-cogs-api.onrender.com}"
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$API_URL/healthz" 2>/dev/null || echo "000")

if [ "$API_STATUS" = "200" ]; then
    success "API is healthy with new credentials"
    echo "API health check passed: $(date)" >> "$ROTATION_LOG"
else
    echo -e "${RED}❌ API health check failed (HTTP $API_STATUS)${NC}"
    echo "API health check FAILED: $(date)" >> "$ROTATION_LOG"
    warning "Investigate before continuing!"
    read -p "Press Enter to continue anyway, or Ctrl+C to abort..."
fi

step 4 "Update Dashboard (Vercel) - If Using Service Key"
action "Go to: https://vercel.com/your-project/settings/environment-variables"
action "Update any Supabase keys if the dashboard uses them directly"
action "Trigger a redeploy"
echo ""
read -p "Press Enter when dashboard is updated (or skip if not applicable)..."
echo "Dashboard updated: $(date)" >> "$ROTATION_LOG"

step 5 "Revoke Old Keys"
warning "IMPORTANT: Only revoke after confirming new keys work!"
action "Go back to Supabase dashboard"
action "Revoke the old service key"
echo ""
read -p "Press Enter when old keys are revoked..."
echo "Old keys revoked: $(date)" >> "$ROTATION_LOG"

step 6 "Document Rotation"
action "Recording rotation in docs/SECRETS_ROTATION.md"
echo ""

ROTATION_ENTRY="| $(date +%Y-%m-%d) | Supabase Service Key | Emergency rotation | $(whoami) |"
echo "Add this entry to docs/SECRETS_ROTATION.md:"
echo "$ROTATION_ENTRY"
echo ""
echo "$ROTATION_ENTRY" >> "$ROTATION_LOG"

step 7 "Final Verification"
action "Running full health check..."
if [ -f "scripts/daily_health_check.sh" ]; then
    ./scripts/daily_health_check.sh
else
    echo "Health check script not found - manual verification required"
fi

echo ""
echo "🎉 Key Rotation Complete"
echo "========================"
success "Rotation logged to: $ROTATION_LOG"
success "Remember to update docs/SECRETS_ROTATION.md"
echo ""
echo "Rotation completed: $(date)" >> "$ROTATION_LOG"
