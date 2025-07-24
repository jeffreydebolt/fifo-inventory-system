# FIFO COGS System - Quick Reference Card

## 🚀 Essential Commands

### Upload New Purchase Lots
```bash
python supabase_lot_uploader.py --file "lots_to_upload.csv"
```

### Run COGS Calculation
```bash
python fifo_calculator_enhanced.py \
  --sales_file "sales_data.csv" \
  --output_dir "month_year_cogs" \
  --log_file "processing.log"
```

### Validate Only (No Processing)
```bash
python fifo_calculator_enhanced.py \
  --sales_file "sales_data.csv" \
  --output_dir "validation" \
  --log_file "validation.log" \
  --validate_only
```

## 📊 Required Data Formats

### Sales CSV Columns
- `SKU` - Product identifier
- `Units Moved` - Quantity sold
- `Month` - Sales month (e.g., "June 2025")

### Purchase Lots CSV Columns
- `lot_id` - Unique identifier
- `po_number` - Purchase order
- `sku` - Product SKU
- `received_date` - Arrival date (YYYY-MM-DD)
- `original_unit_qty` - Initial quantity
- `unit_price` - Cost per unit
- `freight_cost_per_unit` - Shipping cost
- `remaining_unit_qty` - Available quantity

## 🔧 Monthly Workflow

1. **Prepare Sales Data** → Clean CSV with required columns
2. **Upload New Lots** → Use lot uploader script
3. **Run Calculation** → Execute FIFO calculator
4. **Review Outputs** → Check reports in output directory

## 📁 Output Files

- `cogs_attribution_supabase.csv` - Line-by-line COGS details
- `cogs_summary_supabase.csv` - Summary by SKU/month
- `updated_inventory_snapshot_supabase.csv` - Post-processing inventory
- `validation_errors.csv` - Issues found (if any)
- `date_validation_warnings.txt` - Date-related warnings

## ⚠️ Common Issues

| Issue | Solution |
|-------|----------|
| SKU not found | Check spelling, use validation mode |
| Insufficient quantity | Verify inventory, check previous sales |
| Column not found | Use exact column names |
| Date format error | Use "Month Year" or YYYY-MM-DD |

## 🔑 Environment Variables (.env)
```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
```

## 📞 Emergency Commands

### Delete Specific Lots
```bash
python delete_recent_lots.py --po_numbers "PO123,PO456"
```

### Rollback Month
```bash
python rollback_may_2025.py
```

---

*Keep this card handy for quick reference during monthly processing.* 