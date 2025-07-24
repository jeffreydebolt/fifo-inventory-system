# FIFO COGS Calculation System - Complete Guide

## 🎯 What This System Does

The FIFO (First In, First Out) COGS (Cost of Goods Sold) calculation system is designed to:

1. **Track Inventory by Purchase Lots**: Each purchase lot has a unique ID, SKU, quantity, cost, and arrival date
2. **Calculate COGS Using FIFO Logic**: When sales occur, the system allocates costs from the oldest inventory first
3. **Update Inventory in Real-Time**: Automatically reduces remaining quantities in Supabase as sales are processed
4. **Handle Returns**: Processes negative quantities by adding inventory back to the oldest lots
5. **Validate Data**: Ensures sales can be fulfilled from available inventory before processing
6. **Generate Reports**: Creates detailed COGS attribution and summary reports

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.7+
- Supabase account and database
- Required Python packages (see installation below)

### Installation
```bash
# Install required packages
pip install pandas supabase python-dotenv openpyxl

# Clone or download the system files
# Ensure you have the main script: fifo_calculator_enhanced.py
```

### Environment Setup
Create a `.env` file in your project root:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### Basic Usage
```bash
python fifo_calculator_enhanced.py \
  --sales_file "path/to/sales_data.csv" \
  --output_dir "output_directory" \
  --log_file "processing_log.txt"
```

## 📊 Data Format Requirements

### Sales Data Format
Your sales CSV/Excel file must contain these columns:

| Column Name | Description | Format | Example |
|-------------|-------------|--------|---------|
| `SKU` | Product identifier | Text | "ABC123" |
| `Units Moved` | Quantity sold | Number | 50 |
| `Month` | Sales month | Text | "June 2025" |

**Important Notes:**
- Column names are case-sensitive
- The system will try to match variations (e.g., "Units Moved" vs "units moved")
- SKUs are normalized (uppercase, no spaces/special chars) for matching
- Quantities are cleaned (removes $, commas, handles Excel errors)

### Purchase Lots Data (Supabase)
The system expects a `purchase_lots` table with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `lot_id` | UUID | Unique lot identifier |
| `po_number` | Text | Purchase order number |
| `sku` | Text | Product SKU |
| `received_date` | Date | When inventory arrived |
| `original_unit_qty` | Integer | Initial quantity |
| `unit_price` | Decimal | Cost per unit |
| `freight_cost_per_unit` | Decimal | Shipping cost per unit |
| `remaining_unit_qty` | Integer | Current available quantity |

## 🔧 Monthly Update Process

### Step 1: Prepare Sales Data
```bash
# Clean your sales data
# Ensure proper column names and formats
# Save as CSV or Excel file
```

### Step 2: Upload New Purchase Lots
```bash
# Use the lot uploader script
python supabase_lot_uploader.py --file "new_lots.csv"
```

### Step 3: Run COGS Calculation
```bash
python fifo_calculator_enhanced.py \
  --sales_file "sales_june_2025.csv" \
  --output_dir "june_2025_cogs" \
  --log_file "june_processing.log"
```

### Step 4: Review Results
Check the output directory for:
- `cogs_attribution_supabase.csv` - Detailed line-by-line COGS
- `cogs_summary_supabase.csv` - Summary by SKU and month
- `updated_inventory_snapshot_supabase.csv` - Post-processing inventory
- `validation_errors.csv` - Any issues found (if validation failed)

## 🛠️ Advanced Features

### Validation Mode
Run validation without processing:
```bash
python fifo_calculator_enhanced.py \
  --sales_file "sales_data.csv" \
  --output_dir "validation_output" \
  --log_file "validation.log" \
  --validate_only
```

### Returns Processing
The system automatically handles returns (negative quantities):
- Returns are processed before regular sales
- Inventory is added back to the oldest lots first
- Negative COGS are calculated for reporting

### Date Validation
The system warns about sales that occur before inventory arrival:
- Uses FIFO logic to allocate from available inventory
- Logs warnings for future reference
- Continues processing with available inventory

## 📈 Current System Capabilities

### ✅ What Works Well
1. **Robust Data Handling**: Handles various date formats, currency symbols, Excel errors
2. **Flexible Column Matching**: Tries exact, normalized, and partial matches
3. **Real-time Supabase Updates**: Updates inventory quantities as sales are processed
4. **Comprehensive Logging**: Detailed logs for debugging and audit trails
5. **Returns Processing**: Handles negative quantities automatically
6. **Validation System**: Pre-checks sales against available inventory

### ⚠️ Current Limitations
1. **Single-threaded Processing**: Large datasets may be slow
2. **No Rollback Mechanism**: Once processed, changes are permanent
3. **Limited Error Recovery**: Some errors may require manual intervention
4. **No Concurrent User Support**: Only one process can run at a time
5. **Basic Reporting**: Limited visualization and analysis tools

## 🚀 Improvement Roadmap

### Phase 1: Stability & Performance (1-2 months)
1. **Add Rollback Functionality**
   - Create backup snapshots before processing
   - Implement rollback commands for failed runs
   - Add transaction support for atomic operations

2. **Performance Optimization**
   - Implement batch processing for large datasets
   - Add database indexing for faster queries
   - Optimize memory usage for large files

3. **Enhanced Error Handling**
   - Add retry mechanisms for network issues
   - Implement partial processing with resume capability
   - Better error messages and recovery suggestions

### Phase 2: Advanced Features (2-3 months)
1. **Multi-warehouse Support**
   - Handle inventory across multiple locations
   - Warehouse-specific FIFO calculations
   - Transfer between warehouses

2. **Advanced Reporting**
   - Web dashboard for results visualization
   - Automated report generation and emailing
   - Trend analysis and forecasting

3. **Data Quality Tools**
   - Automated data cleaning and validation
   - SKU normalization and mapping tools
   - Duplicate detection and resolution

### Phase 3: Enterprise Features (3-6 months)
1. **User Management**
   - Role-based access control
   - Audit trails for all operations
   - User-specific views and permissions

2. **Integration Capabilities**
   - API endpoints for external systems
   - Webhook support for real-time updates
   - Export to accounting systems

3. **Advanced Analytics**
   - Cost variance analysis
   - Inventory turnover metrics
   - Profitability by SKU/lot

## 🔍 Data Formatting Best Practices

### Sales Data Preparation
1. **Column Headers**: Use exact column names or close variations
2. **SKU Formatting**: 
   - Keep SKUs consistent across systems
   - Avoid special characters when possible
   - Use the same SKU format as purchase lots

3. **Date Formatting**:
   - Use "Month Year" format (e.g., "June 2025")
   - Or use standard date formats (MM/DD/YYYY)
   - Ensure all dates are in the same timezone

4. **Quantity Formatting**:
   - Remove currency symbols ($, €, etc.)
   - Remove commas from numbers
   - Use positive numbers for sales, negative for returns

### Purchase Lots Preparation
1. **SKU Consistency**: Match SKU format exactly with sales data
2. **Date Accuracy**: Ensure received dates are correct for FIFO logic
3. **Cost Accuracy**: Include both unit price and freight costs
4. **Quantity Validation**: Ensure remaining quantities are accurate

## 🐛 Troubleshooting Common Issues

### "SKU not found in inventory"
- Check SKU spelling and format
- Verify SKU exists in purchase lots
- Use SKU mapping suggestions from validation report

### "Insufficient quantity available"
- Check if inventory was already consumed by previous sales
- Verify remaining quantities in purchase lots
- Consider uploading additional inventory

### "Invalid date format"
- Ensure dates are in supported formats
- Check for hidden characters or formatting issues
- Use consistent date format throughout file

### "Column not found"
- Verify column names match expected format
- Check for extra spaces or special characters
- Use the exact column names shown in requirements

## 📞 Support and Maintenance

### Regular Maintenance Tasks
1. **Database Cleanup**: Archive old purchase lots
2. **Log Rotation**: Manage log file sizes
3. **Backup Verification**: Ensure backups are working
4. **Performance Monitoring**: Track processing times

### Getting Help
1. Check the log files for detailed error messages
2. Review validation reports for data issues
3. Verify environment variables are set correctly
4. Test with small datasets first

## 🎯 Success Metrics

Track these metrics to ensure system health:
- Processing time per 1000 sales records
- Validation error rate
- Data accuracy (manual spot checks)
- User satisfaction with reports
- System uptime and reliability

---

*This guide should be updated as the system evolves. For questions or issues, refer to the log files and validation reports for detailed information.* 