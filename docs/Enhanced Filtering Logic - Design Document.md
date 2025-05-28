# Enhanced Filtering Logic - Design Document

## Overview

This document outlines the design for enhancing the filtering capabilities of the COGS Dashboard App, specifically focusing on date range filtering and multi-filter support. These enhancements will provide users with more powerful ways to analyze their COGS data.

## Requirements

Based on user feedback, the enhanced filtering logic should:

1. Support date range filtering (e.g., Q1 2024, Last 6 months, Custom date range)
2. Allow multiple filters to be applied simultaneously (e.g., SKU + date range + category)
3. Maintain performance even with large datasets
4. Provide an intuitive user interface for filter selection

## Technical Approach

We will implement a hybrid approach that combines:
- Client-side filtering for immediate feedback and UI responsiveness
- Server-side (Supabase) filtering for handling large datasets efficiently

### Database Optimizations

To support efficient filtering, we will:

1. **Add Indexes to Key Columns**:
```sql
CREATE INDEX idx_monthly_cogs_summary_date ON monthly_cogs_summary(month);
CREATE INDEX idx_monthly_cogs_summary_sku ON monthly_cogs_summary(sku);
CREATE INDEX idx_monthly_cogs_summary_combined ON monthly_cogs_summary(month, sku);
```

2. **Create Materialized Views for Common Queries**:
```sql
CREATE MATERIALIZED VIEW monthly_cogs_summary_last_12_months AS
SELECT * FROM monthly_cogs_summary
WHERE month >= date_trunc('month', now()) - interval '12 months'
ORDER BY month DESC, sku;
```

### Filter Implementation

#### Date Range Filter

We will implement the following date range options:

1. **Preset Ranges**:
   - Current Month
   - Last Month
   - Last 3 Months
   - Last 6 Months
   - Last 12 Months
   - Year to Date
   - Last Year
   - All Time

2. **Custom Date Range**:
   - Start Date Picker
   - End Date Picker

The date filter will be implemented as a dropdown with preset options and a "Custom Range" option that reveals date pickers.

#### Multi-Filter Implementation

The multi-filter system will:

1. Support filtering by:
   - Date Range
   - SKU (with partial matching)
   - Category (if available)
   - Quantity Thresholds
   - COGS Value Ranges

2. Use a filter state object in React:
```typescript
interface FilterState {
  dateRange: {
    preset: string | null;
    startDate: Date | null;
    endDate: Date | null;
  };
  sku: string | null;
  category: string | null;
  quantityRange: {
    min: number | null;
    max: number | null;
  };
  cogsRange: {
    min: number | null;
    max: number | null;
  };
}
```

3. Translate filter state to Supabase queries:
```typescript
const query = supabase
  .from('monthly_cogs_summary')
  .select('*');

if (filters.dateRange.startDate) {
  query.gte('month', filters.dateRange.startDate);
}
if (filters.dateRange.endDate) {
  query.lte('month', filters.dateRange.endDate);
}
if (filters.sku) {
  query.ilike('sku', `%${filters.sku}%`);
}
// Additional filter conditions...
```

### UI Components

1. **Filter Panel**:
   - Collapsible sidebar or top bar containing all filter controls
   - Clear visual indication of active filters
   - "Clear All Filters" button

2. **Date Range Component**:
   - Dropdown for preset ranges
   - Date pickers for custom range
   - Visual calendar interface

3. **SKU Filter**:
   - Autocomplete text input
   - Support for partial matching
   - Recent or popular SKUs suggestions

4. **Applied Filters Display**:
   - Chips or badges showing currently applied filters
   - One-click removal of individual filters

## Performance Considerations

1. **Debounced Filtering**:
   - Implement debouncing for text inputs to prevent excessive queries
   - Use a 300ms delay before applying text filters

2. **Pagination**:
   - Implement pagination for large result sets
   - Default page size of 25 items with user-configurable options

3. **Caching**:
   - Cache recent query results on the client side
   - Use React Query for efficient data fetching and caching

4. **Progressive Loading**:
   - Show initial results quickly while loading complete dataset
   - Implement skeleton loaders for better UX during data fetching

## Implementation Plan

### Phase 1: Date Range Filtering

1. Create DateRangeFilter component with preset options
2. Implement custom date range selection
3. Modify Supabase queries to include date filtering
4. Add visual indicators for active date filters

### Phase 2: SKU and Category Filtering

1. Implement SKU search with autocomplete
2. Add category filter dropdown (if categories are available)
3. Create filter combination logic
4. Add applied filters display with removal capability

### Phase 3: Advanced Filtering and Optimization

1. Add quantity and COGS range filters
2. Implement performance optimizations (debouncing, caching)
3. Add pagination for large result sets
4. Create filter presets/saved filters functionality

## UI Mockup

```
+-----------------------------------------------+
|  FIFO Inventory                      [Settings]|
+-----------------------------------------------+
| [Dashboard] [Inventory] [Transactions] [Reports]
+-----------------------------------------------+
|                                               |
| Monthly COGS Breakdown                        |
|                                               |
| Filters:                                      |
| Date: [Last 6 Months ▼]                       |
| SKU:  [____________] [Search]                 |
| Category: [All Categories ▼]                  |
|                                               |
| Applied Filters:                              |
| [Last 6 Months ×] [SKU: FBPT4YL24P ×]         |
| [Clear All Filters]                           |
|                                               |
| +-------------------------------------------+ |
| | Month | SKU | Units | Unit Cost | Freight | |
| |-------|-----|-------|-----------|---------|
| | May.. | FB..| 654   | $10,234   | $1,308  | |
| | Apr.. | FB..| 598   | $9,568    | $1,196  | |
| | Mar.. | FB..| 702   | $11,232   | $1,404  | |
| +-------------------------------------------+ |
|                                               |
| [< Prev] Page 1 of 3 [Next >]                 |
+-----------------------------------------------+
```

## Next Steps

1. Implement the DateRangeFilter component
2. Modify the Supabase query builder to support date filtering
3. Update the UI to display active filters
4. Test performance with large datasets
5. Implement additional filter types
