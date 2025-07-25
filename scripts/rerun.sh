#!/bin/bash
# rerun.sh - Run a new FIFO COGS calculation
# Usage: ./rerun.sh --tenant-id TENANT --mode MODE --start-month YYYY-MM-01 [--sales-file FILE] [--lots-file FILE]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
API_URL=${API_URL:-"http://localhost:8000"}
TENANT_ID=""
MODE=""
START_MONTH=""
SALES_FILE=""
LOTS_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --start-month)
            START_MONTH="$2"
            shift 2
            ;;
        --sales-file)
            SALES_FILE="$2"
            shift 2
            ;;
        --lots-file)
            LOTS_FILE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Error: Unknown argument $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$TENANT_ID" ] || [ -z "$MODE" ] || [ -z "$START_MONTH" ]; then
    echo -e "${RED}Error: Missing required arguments${NC}"
    echo "Usage: $0 --tenant-id TENANT --mode MODE --start-month YYYY-MM-01 [--sales-file FILE] [--lots-file FILE]"
    echo "Example: $0 --tenant-id acme-corp --mode fifo --start-month 2024-07-01"
    exit 1
fi

# Validate mode
if [[ ! "$MODE" =~ ^(fifo|avg)$ ]]; then
    echo -e "${RED}Error: Invalid mode '$MODE'. Must be 'fifo' or 'avg'${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 FIFO COGS Run Tool${NC}"
echo "================================"
echo "Tenant ID: $TENANT_ID"
echo "Mode: $MODE"
echo "Start Month: $START_MONTH"
[ -n "$SALES_FILE" ] && echo "Sales File: $SALES_FILE"
[ -n "$LOTS_FILE" ] && echo "Lots File: $LOTS_FILE"
echo ""

# Function to read CSV and convert to JSON
csv_to_json() {
    local file=$1
    local type=$2
    
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: File $file not found${NC}"
        exit 1
    fi
    
    # Simple CSV to JSON conversion (requires python)
    python3 -c "
import csv, json, sys
data = []
with open('$file', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        row['tenant_id'] = '$TENANT_ID'
        data.append(row)
print(json.dumps(data))
"
}

# Prepare request body
REQUEST_BODY="{
  \"tenant_id\": \"$TENANT_ID\",
  \"mode\": \"$MODE\",
  \"start_month\": \"$START_MONTH\""

# Add CSV data if provided
if [ -n "$SALES_FILE" ]; then
    SALES_JSON=$(csv_to_json "$SALES_FILE" "sales")
    REQUEST_BODY="$REQUEST_BODY,
  \"sales_data\": $SALES_JSON"
fi

if [ -n "$LOTS_FILE" ]; then
    LOTS_JSON=$(csv_to_json "$LOTS_FILE" "lots")
    REQUEST_BODY="$REQUEST_BODY,
  \"lots_data\": $LOTS_JSON"
fi

REQUEST_BODY="$REQUEST_BODY
}"

# Start the run
echo -e "${YELLOW}Starting COGS run...${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/runs" \
    -H "Content-Type: application/json" \
    -d "$REQUEST_BODY")

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start run${NC}"
    exit 1
fi

# Extract run_id
RUN_ID=$(echo "$RESPONSE" | grep -o '"run_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"run_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

if [ -z "$RUN_ID" ]; then
    echo -e "${RED}Error: Could not extract run_id from response${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Run started: $RUN_ID${NC}"
echo ""

# Poll for completion
echo -e "${YELLOW}Polling for completion...${NC}"
MAX_ATTEMPTS=60  # 5 minutes with 5-second intervals
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 5
    
    STATUS_RESPONSE=$(curl -s "$API_URL/api/v1/runs/$RUN_ID")
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    
    echo -ne "\rStatus: $STATUS (attempt $((ATTEMPT+1))/$MAX_ATTEMPTS)"
    
    case $STATUS in
        "completed")
            echo ""
            echo -e "${GREEN}✅ Run completed successfully!${NC}"
            echo "Run ID: $RUN_ID"
            exit 0
            ;;
        "failed")
            echo ""
            echo -e "${RED}❌ Run failed!${NC}"
            echo "Response: $STATUS_RESPONSE"
            exit 1
            ;;
        "rolled_back")
            echo ""
            echo -e "${RED}❌ Run was rolled back!${NC}"
            exit 1
            ;;
    esac
    
    ATTEMPT=$((ATTEMPT + 1))
done

echo ""
echo -e "${RED}❌ Timeout: Run did not complete within 5 minutes${NC}"
exit 1