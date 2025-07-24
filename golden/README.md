# Golden Test Files

This folder contains trusted baseline files for parity testing during refactoring.

## Files

- **`golden_sales.csv`** - Clean sales data from June 2025 (successful run)
- **`golden_cogs_attribution.csv`** - Expected COGS attribution output
- **`golden_cogs_summary.csv`** - Expected COGS summary output  
- **`golden_inventory_snapshot.csv`** - Expected post-processing inventory state

## Usage for Parity Testing

### Before Refactoring
1. Run the current system with `golden_sales.csv`
2. Verify outputs match the golden files exactly
3. Document any differences

### During Refactoring
1. After each significant change, run the new system with `golden_sales.csv`
2. Compare outputs against golden files
3. Ensure no regression in calculations

### Comparison Commands
```bash
# Compare COGS attribution
diff golden/golden_cogs_attribution.csv new_outputs/cogs_attribution.csv

# Compare COGS summary  
diff golden/golden_cogs_summary.csv new_outputs/cogs_summary.csv

# Compare inventory snapshots
diff golden/golden_inventory_snapshot.csv new_outputs/inventory_snapshot.csv
```

### Automated Testing
Consider creating automated tests that:
1. Load `golden_sales.csv`
2. Run the calculation
3. Compare results against golden files
4. Fail if differences exceed tolerance

## Notes
- These files represent a known-good state from June 2025
- Any changes to the calculation logic should maintain compatibility with these outputs
- Update golden files only when intentionally changing business logic 