#!/bin/bash
# csv_validation_response.sh - Parse CSV validation errors and provide user-friendly guidance
# Use when users report CSV upload failures

set -e

echo "📋 FIFO COGS CSV Validation Helper"
echo "==================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
fix() { echo -e "${GREEN}   Fix: $1${NC}"; }

# Show usage if no arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <csv_file> [lots|sales]"
    echo ""
    echo "Examples:"
    echo "  $0 my_sales.csv sales"
    echo "  $0 inventory_lots.csv lots"
    echo ""
    echo "This script validates CSV files and provides helpful error messages."
    exit 1
fi

CSV_FILE="$1"
FILE_TYPE="${2:-auto}"

if [ ! -f "$CSV_FILE" ]; then
    error "File not found: $CSV_FILE"
    exit 1
fi

echo "Analyzing: $CSV_FILE"
echo "File type: $FILE_TYPE"
echo ""

# Basic file checks
echo "📝 Basic File Checks"
echo "--------------------"

# Check for BOM (Byte Order Mark)
if head -c 3 "$CSV_FILE" | grep -q $'\xef\xbb\xbf'; then
    error "File has UTF-8 BOM (Byte Order Mark)"
    fix "Open in a text editor and save as UTF-8 without BOM"
    fix "Or run: sed -i '1s/^\xEF\xBB\xBF//' \"$CSV_FILE\""
fi

# Check line endings
if file "$CSV_FILE" | grep -q "CRLF"; then
    info "File has Windows line endings (CRLF) - this is usually OK"
fi

# Check encoding
ENCODING=$(file -b --mime-encoding "$CSV_FILE")
echo "Encoding: $ENCODING"
if [ "$ENCODING" != "utf-8" ] && [ "$ENCODING" != "us-ascii" ]; then
    error "File encoding is $ENCODING (expected UTF-8)"
    fix "Convert with: iconv -f $ENCODING -t UTF-8 \"$CSV_FILE\" > fixed.csv"
fi

echo ""
echo "📊 Column Analysis"
echo "------------------"

# Get header row
HEADER=$(head -1 "$CSV_FILE" | tr -d '\r')
echo "Columns found: $HEADER"
echo ""

# Expected columns for each file type
SALES_REQUIRED="sale_id,sku,sale_date,quantity_sold"
LOTS_REQUIRED="lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price"

# Check required columns based on file type
check_columns() {
    local required="$1"
    local header_lower=$(echo "$HEADER" | tr '[:upper:]' '[:lower:]')
    
    IFS=',' read -ra COLS <<< "$required"
    MISSING=""
    
    for col in "${COLS[@]}"; do
        if ! echo "$header_lower" | grep -qi "$col"; then
            MISSING="$MISSING $col"
        fi
    done
    
    if [ -n "$MISSING" ]; then
        error "Missing required columns:$MISSING"
        return 1
    else
        echo -e "${GREEN}✅ All required columns present${NC}"
        return 0
    fi
}

if [ "$FILE_TYPE" = "sales" ] || echo "$HEADER" | grep -qi "sale_id"; then
    echo "Detected: Sales file"
    check_columns "$SALES_REQUIRED"
elif [ "$FILE_TYPE" = "lots" ] || echo "$HEADER" | grep -qi "lot_id"; then
    echo "Detected: Lots/Inventory file"
    check_columns "$LOTS_REQUIRED"
else
    info "Could not auto-detect file type. Specify 'sales' or 'lots' as second argument."
fi

echo ""
echo "📅 Date Format Check"
echo "--------------------"

# Sample some dates from the file
DATES=$(awk -F',' 'NR>1 {for(i=1;i<=NF;i++) if($i ~ /[0-9]{4}/ || $i ~ /[0-9]{2}\/[0-9]{2}/) print $i}' "$CSV_FILE" | head -5)

if [ -n "$DATES" ]; then
    echo "Sample date values found:"
    echo "$DATES" | while read date; do
        echo "  $date"
    done
    echo ""
    info "Expected format: YYYY-MM-DD or ISO 8601 (2024-07-15T10:00:00Z)"
    
    # Check for common bad formats
    if echo "$DATES" | grep -qE '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'; then
        error "Detected MM/DD/YYYY format"
        fix "Convert to YYYY-MM-DD format"
    fi
fi

echo ""
echo "🔢 Data Quality Check"
echo "---------------------"

ROW_COUNT=$(wc -l < "$CSV_FILE" | tr -d ' ')
echo "Total rows: $ROW_COUNT (including header)"

# Check for empty rows
EMPTY_ROWS=$(awk -F',' 'NF==0 || /^[,\s]*$/' "$CSV_FILE" | wc -l | tr -d ' ')
if [ "$EMPTY_ROWS" -gt 0 ]; then
    error "Found $EMPTY_ROWS empty rows"
    fix "Remove empty rows from the file"
fi

# Check column count consistency
EXPECTED_COLS=$(echo "$HEADER" | tr ',' '\n' | wc -l | tr -d ' ')
INCONSISTENT=$(awk -F',' -v exp="$EXPECTED_COLS" 'NF!=exp {count++} END {print count+0}' "$CSV_FILE")
if [ "$INCONSISTENT" -gt 1 ]; then  # Allow for header
    error "Found rows with inconsistent column counts (expected $EXPECTED_COLS)"
    fix "Ensure all rows have the same number of columns"
fi

echo ""
echo "📋 Sample Valid Format"
echo "----------------------"

if [ "$FILE_TYPE" = "sales" ] || echo "$HEADER" | grep -qi "sale_id"; then
    echo "Example valid sales CSV:"
    echo ""
    echo "sale_id,sku,sale_date,quantity_sold,tenant_id"
    echo "SALE001,WIDGET-A,2024-07-20T10:00:00Z,100,acme-corp"
    echo "SALE002,WIDGET-B,2024-07-21T14:30:00Z,50,acme-corp"
elif [ "$FILE_TYPE" = "lots" ] || echo "$HEADER" | grep -qi "lot_id"; then
    echo "Example valid lots CSV:"
    echo ""
    echo "lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit,tenant_id"
    echo "LOT001,WIDGET-A,2024-07-01T00:00:00Z,500,500,10.00,1.00,acme-corp"
    echo "LOT002,WIDGET-B,2024-07-05T00:00:00Z,300,300,15.50,1.25,acme-corp"
fi

echo ""
echo "==================================="
echo "Validation complete"
