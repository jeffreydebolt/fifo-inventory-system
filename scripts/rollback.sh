#!/bin/bash
# rollback.sh - Rollback a FIFO COGS run
# Usage: ./rollback.sh <RUN_ID> [--confirm]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Missing RUN_ID${NC}"
    echo "Usage: $0 <RUN_ID> [--confirm]"
    echo "Example: $0 RUN_123456 --confirm"
    exit 1
fi

RUN_ID=$1
CONFIRM=${2:-""}

# Source environment or use defaults
SUPABASE_URL=${SUPABASE_URL:-""}
API_URL=${API_URL:-"http://localhost:8000"}

echo -e "${YELLOW}🔄 FIFO COGS Rollback Tool${NC}"
echo "================================"
echo "Run ID: $RUN_ID"
echo ""

# Function to check run details
check_run() {
    echo -e "${YELLOW}Fetching run details...${NC}"
    
    if [ -n "$SUPABASE_URL" ]; then
        # Direct database query
        RESULT=$(psql "$SUPABASE_URL" -t -c "
            SELECT status, tenant_id, created_at 
            FROM cogs_runs 
            WHERE run_id = '$RUN_ID'
            LIMIT 1;
        ")
        
        if [ -z "$RESULT" ]; then
            echo -e "${RED}Error: Run $RUN_ID not found${NC}"
            exit 1
        fi
        
        echo "Run found: $RESULT"
    else
        # API query
        RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID")
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to fetch run details${NC}"
            exit 1
        fi
        echo "Run details: $RESPONSE"
    fi
}

# Function to perform rollback
perform_rollback() {
    if [ "$CONFIRM" != "--confirm" ]; then
        echo -e "${YELLOW}⚠️  DRY RUN MODE${NC}"
        echo "This would rollback run: $RUN_ID"
        echo ""
        echo "To actually perform the rollback, run:"
        echo -e "${GREEN}$0 $RUN_ID --confirm${NC}"
        exit 0
    fi
    
    echo -e "${YELLOW}Performing rollback...${NC}"
    
    # Use CLI if available, otherwise API
    if [ -f "app/cli.py" ]; then
        python -m app.cli rollback "$RUN_ID" --confirm
    else
        RESPONSE=$(curl -s -X POST "$API_URL/api/v1/runs/$RUN_ID/rollback" \
            -H "Content-Type: application/json")
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Rollback completed successfully${NC}"
            echo "Response: $RESPONSE"
        else
            echo -e "${RED}❌ Rollback failed${NC}"
            exit 1
        fi
    fi
}

# Main execution
check_run
perform_rollback

echo ""
echo -e "${GREEN}✅ Operation completed${NC}"