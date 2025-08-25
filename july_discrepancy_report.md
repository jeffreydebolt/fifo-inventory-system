# July 2025 Sales Processing - Detailed Discrepancy Report

## Overview
- **Input File**: july_sales_converted.csv
- **Total Input Quantity**: 32,259 units
- **Total Processed Quantity**: 31,877 units  
- **Discrepancy**: 382 units (1.18% of total)

## Detailed Breakdown

### 1. CRSB654243 - Insufficient Inventory
- **Requested**: 1,863 units
- **Fulfilled**: 1,485 units
- **Unfulfilled**: 378 units (20.3% of requested)
- **Reason**: Only 1,485 units available in inventory (Lot ST0192)
- **Available Inventory**: 
  - Lot ST0192: 1,485 units @ $1.30/unit + $0.33 freight
  - All inventory was consumed, leaving 0 remaining

### 2. PETS500FGR - No Inventory Available
- **Requested**: 4 units
- **Fulfilled**: 0 units
- **Unfulfilled**: 4 units (100% of requested)
- **Reason**: No inventory available for this SKU
- **Status**: SKU not found in purchase_lots table

## Impact Analysis

### Financial Impact
- **Unfulfilled COGS**: Approximately $622.74
  - CRSB654243: 378 units × $1.63 = $616.14
  - PETS500FGR: 4 units × ~$1.65 (estimated) = $6.60

### Business Impact
- 98.82% of requested quantities were successfully fulfilled
- Only 2 out of 112 SKUs had inventory issues
- The system correctly handled inventory constraints

## Recommendations

1. **Inventory Replenishment**:
   - CRSB654243: Reorder immediately - high demand (1,863 units/month)
   - PETS500FGR: Investigate if this is a new SKU or discontinued

2. **System Behavior**:
   - The FIFO system correctly prevented overselling
   - All available inventory was properly allocated
   - The warning system properly logged insufficient inventory

## Summary
The 382-unit discrepancy is entirely explained by inventory constraints:
- 378 units: CRSB654243 partial fulfillment
- 4 units: PETS500FGR no inventory
- **Total: 382 units** ✓