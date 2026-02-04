#!/bin/bash
# csv_validate.sh - Validate CSV files for FIFO COGS system
# Usage: ./csv_validate.sh <TYPE> <FILE>
# TYPE: sales or lots

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -ne 2 ]; then
    echo -e "${RED}Error: Invalid arguments${NC}"
    echo "Usage: $0 <TYPE> <FILE>"
    echo "  TYPE: sales or lots"
    echo "  FILE: path to CSV file"
    echo ""
    echo "Example: $0 sales sales_2024.csv"
    echo "Example: $0 lots inventory_lots.csv"
    exit 1
fi

TYPE=$1
FILE=$2

# Check if file exists
if [ ! -f "$FILE" ]; then
    echo -e "${RED}Error: File '$FILE' not found${NC}"
    exit 1
fi

echo -e "${BLUE}📋 CSV Validation Tool${NC}"
echo "================================"
echo "Type: $TYPE"
echo "File: $FILE"
echo ""

# Define required headers
declare -a SALES_HEADERS=("sale_id" "sku" "sale_date" "quantity_sold")
declare -a LOTS_HEADERS=("lot_id" "sku" "received_date" "original_quantity" "remaining_quantity" "unit_price" "freight_cost_per_unit")

# Function to check headers
check_headers() {
    local file=$1
    shift
    local required_headers=("$@")
    local missing_headers=()
    local has_errors=false
    
    # Get first line (headers)
    HEADER_LINE=$(head -n 1 "$file")
    
    # Check for each required header
    for header in "${required_headers[@]}"; do
        if ! echo "$HEADER_LINE" | grep -q "$header"; then
            missing_headers+=("$header")
            has_errors=true
        fi
    done
    
    return $([ "$has_errors" = true ] && echo 1 || echo 0)
}

# Function to validate date format
check_date_format() {
    local file=$1
    local date_column=$2
    local invalid_count=0
    
    # Get column index
    HEADER_LINE=$(head -n 1 "$file")
    COL_INDEX=$(echo "$HEADER_LINE" | tr ',' '\n' | grep -n "^$date_column$" | cut -d: -f1)
    
    if [ -z "$COL_INDEX" ]; then
        return 0  # Column not found, already reported
    fi
    
    # Check date format in first few rows
    invalid_count=$(tail -n +2 "$file" | head -20 | cut -d, -f"$COL_INDEX" | grep -vE '^[0-9]{4}-[0-9]{2}-[0-9]{2}' | wc -l)
    
    if [ "$invalid_count" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warning: Found $invalid_count invalid dates in $date_column column${NC}"
        echo "   Expected format: YYYY-MM-DD (e.g., 2024-07-20)"
        echo ""
    fi
}

# Function to check for empty values
check_empty_values() {
    local file=$1
    local total_rows=$(tail -n +2 "$file" | wc -l)
    local empty_cells=$(tail -n +2 "$file" | grep -E '(^,|,,|,$)' | wc -l)
    
    if [ "$empty_cells" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warning: Found $empty_cells rows with empty values${NC}"
        echo "   All fields should have values"
        echo ""
    fi
}

# Main validation
case $TYPE in
    "sales")
        echo -e "${YELLOW}Validating Sales CSV...${NC}"
        
        if ! check_headers "$FILE" "${SALES_HEADERS[@]}"; then
            echo -e "${RED}❌ Missing required headers:${NC}"
            for header in "${missing_headers[@]}"; do
                echo "   - $header"
            done
            echo ""
            echo -e "${GREEN}Required headers for sales CSV:${NC}"
            echo "   sale_id,sku,sale_date,quantity_sold"
            echo ""
            echo -e "${BLUE}Example sales.csv:${NC}"
            echo "sale_id,sku,sale_date,quantity_sold"
            echo "SALE001,WIDGET-A,2024-07-20,100"
            echo "SALE002,WIDGET-B,2024-07-21,50"
            exit 1
        fi
        
        check_date_format "$FILE" "sale_date"
        check_empty_values "$FILE"
        
        echo -e "${GREEN}✅ Sales CSV validation passed!${NC}"
        ;;
        
    "lots")
        echo -e "${YELLOW}Validating Lots CSV...${NC}"
        
        if ! check_headers "$FILE" "${LOTS_HEADERS[@]}"; then
            echo -e "${RED}❌ Missing required headers:${NC}"
            for header in "${missing_headers[@]}"; do
                echo "   - $header"
            done
            echo ""
            echo -e "${GREEN}Required headers for lots CSV:${NC}"
            echo "   lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit"
            echo ""
            echo -e "${BLUE}Example lots.csv:${NC}"
            echo "lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit"
            echo "LOT001,WIDGET-A,2024-07-01,500,500,10.00,1.00"
            echo "LOT002,WIDGET-A,2024-07-15,300,300,10.50,1.20"
            exit 1
        fi
        
        check_date_format "$FILE" "received_date"
        check_empty_values "$FILE"
        
        # Additional validation for lots
        echo -e "${YELLOW}Checking numeric values...${NC}"
        NUMERIC_ERRORS=$(tail -n +2 "$FILE" | awk -F, '{
            if ($4 !~ /^[0-9]+$/ || $5 !~ /^[0-9]+$/) print "Row " NR ": quantities must be integers"
            if ($6 !~ /^[0-9]+\.?[0-9]*$/ || $7 !~ /^[0-9]+\.?[0-9]*$/) print "Row " NR ": prices must be numeric"
        }' | head -5)
        
        if [ -n "$NUMERIC_ERRORS" ]; then
            echo -e "${RED}❌ Numeric validation errors:${NC}"
            echo "$NUMERIC_ERRORS"
            echo "   (showing first 5 errors)"
            exit 1
        fi
        
        echo -e "${GREEN}✅ Lots CSV validation passed!${NC}"
        ;;
        
    *)
        echo -e "${RED}Error: Invalid type '$TYPE'. Must be 'sales' or 'lots'${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ CSV file is valid and ready for processing!${NC}"