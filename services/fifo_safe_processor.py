#!/usr/bin/env python3
"""
FIFO SAFE PROCESSOR
Enhanced FIFO processor with comprehensive error recovery.
Isolates errors to prevent one bad SKU from stopping processing of good SKUs.
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import os
import json

# Import existing production components
from error_recovery_manager import ErrorRecoveryManager, ErrorCategory, ErrorSeverity

class FIFOSafeProcessor:
    """
    Enhanced FIFO processor that handles errors gracefully.
    Wraps existing FIFO logic with comprehensive error handling.
    """
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or f"safe_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize error recovery manager
        self.error_manager = ErrorRecoveryManager(os.path.join(self.output_dir, "errors"))
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        log_file = os.path.join(self.output_dir, "processing.log")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Processing statistics
        self.stats = {
            'total_skus': 0,
            'processed_skus': 0,
            'skipped_skus': 0,
            'total_sales': 0,
            'processed_sales': 0,
            'total_errors': 0,
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # Results storage
        self.successful_attributions = []
        self.successful_summaries = []
        self.skipped_skus = []
    
    def validate_sales_data(self, sales_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate sales data and identify potential issues before processing.
        Returns (clean_data, warnings)
        """
        warnings = []
        original_count = len(sales_df)
        
        # Check required columns
        required_cols = ['SKU', 'Quantity_Sold', 'Sale_Date']
        missing_cols = [col for col in required_cols if col not in sales_df.columns]
        
        if missing_cols:
            error_msg = f"Missing required columns: {missing_cols}"
            self.error_manager.record_error(
                category=ErrorCategory.VALIDATION_ERROR,
                severity=ErrorSeverity.CRITICAL,
                sku="SYSTEM",
                message=error_msg,
                suggested_fix="Ensure sales data contains all required columns"
            )
            raise ValueError(error_msg)
        
        # Clean and validate data
        clean_df = sales_df.copy()
        
        # Remove rows with missing SKU
        before_sku_clean = len(clean_df)
        clean_df = clean_df.dropna(subset=['SKU'])
        after_sku_clean = len(clean_df)
        if before_sku_clean != after_sku_clean:
            warnings.append(f"Removed {before_sku_clean - after_sku_clean} rows with missing SKU")
        
        # Remove rows with zero or negative quantities
        before_qty_clean = len(clean_df)
        clean_df = clean_df[clean_df['Quantity_Sold'] > 0]
        after_qty_clean = len(clean_df)
        if before_qty_clean != after_qty_clean:
            warnings.append(f"Removed {before_qty_clean - after_qty_clean} rows with invalid quantities")
        
        # Check for duplicate sales (same SKU, date, quantity)
        duplicates = clean_df.duplicated(subset=['SKU', 'Sale_Date', 'Quantity_Sold'])
        if duplicates.any():
            dup_count = duplicates.sum()
            warnings.append(f"Found {dup_count} potential duplicate sales records")
            
            # Log details but don't remove (might be legitimate)
            for idx, row in clean_df[duplicates].iterrows():
                self.error_manager.record_error(
                    category=ErrorCategory.DATA_CONFLICT,
                    severity=ErrorSeverity.MEDIUM,
                    sku=row['SKU'],
                    message=f"Potential duplicate sale: {row['Quantity_Sold']} units on {row['Sale_Date']}",
                    suggested_fix="Verify if this is a legitimate duplicate sale or data error"
                )
        
        self.logger.info(f"Sales validation: {original_count} → {len(clean_df)} records ({len(warnings)} warnings)")
        return clean_df, warnings
    
    def validate_inventory_data(self, lots_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Validate inventory lots data.
        Returns (clean_data, warnings)
        """
        warnings = []
        original_count = len(lots_df)
        
        # Check for negative remaining quantities
        negative_remaining = lots_df[lots_df['Remaining_Unit_Qty'] < 0]
        if not negative_remaining.empty:
            warnings.append(f"Found {len(negative_remaining)} lots with negative remaining quantities")
            for idx, lot in negative_remaining.iterrows():
                self.error_manager.record_error(
                    category=ErrorCategory.DATA_CONFLICT,
                    severity=ErrorSeverity.HIGH,
                    sku=lot.get('SKU', 'UNKNOWN'),
                    message=f"Lot {lot.get('Lot_ID', 'UNKNOWN')} has negative remaining quantity: {lot['Remaining_Unit_Qty']}",
                    suggested_fix="Check lot data for errors or adjust quantities"
                )
        
        # Check for remaining > original quantities
        invalid_quantities = lots_df[lots_df['Remaining_Unit_Qty'] > lots_df['Original_Unit_Qty']]
        if not invalid_quantities.empty:
            warnings.append(f"Found {len(invalid_quantities)} lots with remaining > original quantities")
            for idx, lot in invalid_quantities.iterrows():
                self.error_manager.record_error(
                    category=ErrorCategory.DATA_CONFLICT,
                    severity=ErrorSeverity.HIGH,
                    sku=lot.get('SKU', 'UNKNOWN'),
                    message=f"Lot {lot.get('Lot_ID', 'UNKNOWN')} has impossible quantities: remaining {lot['Remaining_Unit_Qty']} > original {lot['Original_Unit_Qty']}",
                    suggested_fix="Correct lot quantities or check for data corruption"
                )
        
        # Check for cost anomalies
        if 'Unit_Price' in lots_df.columns:
            for sku in lots_df['SKU'].unique():
                sku_lots = lots_df[lots_df['SKU'] == sku]
                if len(sku_lots) > 1:
                    avg_cost = sku_lots['Unit_Price'].mean()
                    for idx, lot in sku_lots.iterrows():
                        cost_variance = ((lot['Unit_Price'] - avg_cost) / avg_cost) * 100
                        if abs(cost_variance) > 50:  # More than 50% variance
                            self.error_manager.handle_cost_anomaly(
                                sku=sku,
                                current_cost=lot['Unit_Price'],
                                average_cost=avg_cost,
                                variance_percent=cost_variance
                            )
        
        self.logger.info(f"Inventory validation: {original_count} lots ({len(warnings)} warnings)")
        return lots_df, warnings
    
    def process_sku_safely(self, 
                          sku: str, 
                          sku_sales: pd.DataFrame, 
                          sku_lots: pd.DataFrame,
                          existing_fifo_processor) -> Optional[Dict[str, Any]]:
        """
        Process a single SKU with comprehensive error handling.
        Returns processing results or None if SKU should be skipped.
        """
        try:
            self.logger.info(f"Processing SKU {sku}: {len(sku_sales)} sales, {len(sku_lots)} lots")
            
            # Pre-processing validation
            total_sales = sku_sales['Quantity_Sold'].sum()
            total_available = sku_lots['Remaining_Unit_Qty'].sum()
            
            # Check for missing lots
            if sku_lots.empty:
                self.error_manager.handle_missing_lots(
                    sku=sku,
                    sales_qty=int(total_sales),
                    sale_date=str(sku_sales['Sale_Date'].min())
                )
                return None
            
            # Check for insufficient inventory
            if total_available < total_sales:
                lot_details = []
                for _, lot in sku_lots.iterrows():
                    lot_details.append({
                        'lot_id': lot.get('Lot_ID', 'UNKNOWN'),
                        'received_date': str(lot.get('Received_Date', '')),
                        'remaining': int(lot['Remaining_Unit_Qty'])
                    })
                
                self.error_manager.handle_negative_inventory(
                    sku=sku,
                    requested_qty=int(total_sales),
                    available_qty=int(total_available),
                    lot_details=lot_details
                )
                return None
            
            # Check for date mismatches
            earliest_lot_date = sku_lots['Received_Date'].min()
            earliest_sale_date = sku_sales['Sale_Date'].min()
            
            if pd.notna(earliest_lot_date) and pd.notna(earliest_sale_date):
                if earliest_sale_date < earliest_lot_date:
                    self.error_manager.handle_date_mismatch(
                        sku=sku,
                        sale_date=str(earliest_sale_date),
                        earliest_lot_date=str(earliest_lot_date)
                    )
                    # Continue processing with warning (not blocking)
            
            # Attempt FIFO processing using existing processor
            # This would integrate with the existing fifo_calculator_supabase.py logic
            result = self._process_fifo_for_sku(sku, sku_sales, sku_lots, existing_fifo_processor)
            
            if result:
                self.logger.info(f"✅ Successfully processed SKU {sku}: COGS ${result.get('total_cogs', 0):.2f}")
                return result
            else:
                self.logger.warning(f"⚠️ SKU {sku} processing returned no results")
                return None
                
        except Exception as e:
            # Catch any unexpected errors and isolate them
            self.logger.error(f"❌ Error processing SKU {sku}: {e}")
            self.error_manager.record_error(
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.HIGH,
                sku=sku,
                message=f"Unexpected error during processing: {str(e)}",
                suggested_fix="Review SKU data and processing logs for details",
                data_context={'exception': str(e), 'exception_type': type(e).__name__}
            )
            return None
    
    def _process_fifo_for_sku(self, 
                             sku: str, 
                             sku_sales: pd.DataFrame, 
                             sku_lots: pd.DataFrame,
                             existing_processor) -> Optional[Dict[str, Any]]:
        """
        Wrapper for existing FIFO processing logic.
        This would integrate with the production fifo_calculator_supabase.py
        """
        # This is a placeholder for integration with existing FIFO logic
        # In real implementation, this would call the existing FIFO calculator
        # while maintaining error isolation
        
        try:
            # Sort lots by date (FIFO order)
            sorted_lots = sku_lots.sort_values('Received_Date')
            
            # Sort sales by date
            sorted_sales = sku_sales.sort_values('Sale_Date')
            
            # Simulate FIFO processing (in real implementation, use existing logic)
            attributions = []
            remaining_lots = sorted_lots.copy()
            
            for _, sale in sorted_sales.iterrows():
                sale_qty = sale['Quantity_Sold']
                sale_date = sale['Sale_Date']
                remaining_to_allocate = sale_qty
                
                for lot_idx, lot in remaining_lots.iterrows():
                    if remaining_to_allocate <= 0:
                        break
                    
                    available = lot['Remaining_Unit_Qty']
                    if available <= 0:
                        continue
                    
                    allocated = min(remaining_to_allocate, available)
                    
                    # Create attribution record
                    attribution = {
                        'sale_date': sale_date,
                        'sku': sku,
                        'lot_id': lot.get('Lot_ID', 'UNKNOWN'),
                        'allocated_qty': allocated,
                        'unit_cost': lot.get('Unit_Price', 0) + lot.get('Freight_Cost_Per_Unit', 0),
                        'total_cost': allocated * (lot.get('Unit_Price', 0) + lot.get('Freight_Cost_Per_Unit', 0))
                    }
                    attributions.append(attribution)
                    
                    # Update remaining quantity
                    remaining_lots.loc[lot_idx, 'Remaining_Unit_Qty'] -= allocated
                    remaining_to_allocate -= allocated
                
                if remaining_to_allocate > 0:
                    # This should have been caught earlier, but double-check
                    raise ValueError(f"Could not fully allocate sale: {remaining_to_allocate} units remaining")
            
            # Calculate totals
            total_cogs = sum(attr['total_cost'] for attr in attributions)
            total_qty = sum(attr['allocated_qty'] for attr in attributions)
            
            return {
                'sku': sku,
                'attributions': attributions,
                'total_cogs': total_cogs,
                'total_quantity': total_qty,
                'average_cost': total_cogs / total_qty if total_qty > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"FIFO processing error for {sku}: {e}")
            raise
    
    def process_batch_safely(self, 
                           sales_df: pd.DataFrame, 
                           lots_df: pd.DataFrame,
                           existing_processor=None) -> Dict[str, Any]:
        """
        Process entire batch with comprehensive error handling and isolation.
        """
        self.logger.info("Starting safe batch processing...")
        self.stats['start_time'] = datetime.now()
        
        # Validate input data
        try:
            clean_sales, sales_warnings = self.validate_sales_data(sales_df)
            clean_lots, lots_warnings = self.validate_inventory_data(lots_df)
        except ValueError as e:
            # Critical validation error - cannot continue
            self.logger.error(f"Critical validation error: {e}")
            return self._generate_failure_report(str(e))
        
        # Get unique SKUs and prepare for processing
        all_skus = set(clean_sales['SKU'].unique()) | set(clean_lots['SKU'].unique())
        sales_skus = set(clean_sales['SKU'].unique())
        inventory_skus = set(clean_lots['SKU'].unique())
        
        self.stats['total_skus'] = len(all_skus)
        self.stats['total_sales'] = len(clean_sales)
        
        self.logger.info(f"Processing {len(all_skus)} unique SKUs")
        self.logger.info(f"SKUs with sales: {len(sales_skus)}")
        self.logger.info(f"SKUs with inventory: {len(inventory_skus)}")
        
        # Process each SKU individually with error isolation
        successful_results = []
        
        for sku in sorted(all_skus):
            sku_sales = clean_sales[clean_sales['SKU'] == sku]
            sku_lots = clean_lots[clean_lots['SKU'] == sku]
            
            # Only process SKUs that have both sales and inventory
            if sku_sales.empty:
                self.logger.info(f"Skipping {sku}: no sales data")
                continue
            
            if sku_lots.empty:
                # This will be handled by process_sku_safely
                pass
            
            # Process SKU with error isolation
            result = self.process_sku_safely(sku, sku_sales, sku_lots, existing_processor)
            
            if result:
                successful_results.append(result)
                self.stats['processed_skus'] += 1
                self.stats['processed_sales'] += len(sku_sales)
            else:
                self.skipped_skus.append(sku)
                self.stats['skipped_skus'] += 1
        
        # Finalize processing
        self.stats['end_time'] = datetime.now()
        self.stats['total_errors'] = len(self.error_manager.errors)
        
        # Generate comprehensive results
        return self._generate_processing_report(successful_results)
    
    def _generate_processing_report(self, successful_results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive processing report"""
        
        # Export error reports
        error_reports = self.error_manager.export_error_report()
        
        # Create summary statistics
        processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # Generate success/failure breakdown
        can_continue, processable_skus = self.error_manager.can_continue_processing()
        
        report = {
            'status': 'completed_with_errors' if self.error_manager.errors else 'completed_successfully',
            'processing_time_seconds': processing_time,
            'statistics': self.stats.copy(),
            'success_rate': {
                'skus': (self.stats['processed_skus'] / self.stats['total_skus'] * 100) if self.stats['total_skus'] > 0 else 0,
                'sales': (self.stats['processed_sales'] / self.stats['total_sales'] * 100) if self.stats['total_sales'] > 0 else 0
            },
            'error_summary': self.error_manager._get_error_summary(),
            'can_continue_processing': can_continue,
            'processable_skus': processable_skus,
            'actionable_steps': self.error_manager.get_actionable_steps(),
            'successful_results': successful_results,
            'skipped_skus': self.skipped_skus,
            'output_files': {
                'processing_log': os.path.join(self.output_dir, "processing.log"),
                'error_reports': error_reports,
                'results_json': os.path.join(self.output_dir, "processing_results.json")
            }
        }
        
        # Export detailed results
        results_file = report['output_files']['results_json']
        with open(results_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Log summary
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING SUMMARY:")
        self.logger.info(f"✅ Processed: {self.stats['processed_skus']}/{self.stats['total_skus']} SKUs ({report['success_rate']['skus']:.1f}%)")
        self.logger.info(f"❌ Errors: {self.stats['total_errors']}")
        self.logger.info(f"⏱ Processing time: {processing_time:.2f} seconds")
        
        if self.error_manager.errors:
            self.logger.info("🔍 Error Summary:")
            error_summary = self.error_manager._generate_summary_report()
            for line in error_summary.split('\n'):
                self.logger.info(line)
        
        return report
    
    def _generate_failure_report(self, error_message: str) -> Dict[str, Any]:
        """Generate report for critical failures"""
        return {
            'status': 'failed',
            'error': error_message,
            'statistics': self.stats,
            'processing_time_seconds': 0,
            'success_rate': {'skus': 0, 'sales': 0},
            'actionable_steps': ['Fix critical validation errors before retrying']
        }

# Integration helpers
def create_safe_wrapper_for_existing_processor(existing_processor_func, output_dir: str = None):
    """
    Create a safe wrapper around existing FIFO processing function.
    This allows gradual integration with existing production code.
    """
    
    def safe_wrapper(*args, **kwargs):
        processor = FIFOSafeProcessor(output_dir)
        
        # Extract data from arguments (adapt based on existing function signature)
        # This would need to be customized based on how the existing processor works
        
        try:
            # Call existing processor with error handling
            result = existing_processor_func(*args, **kwargs)
            
            # Enhance result with error reporting
            if processor.error_manager.errors:
                result['errors'] = processor.error_manager.export_error_report()
                result['error_summary'] = processor.error_manager._generate_summary_report()
            
            return result
            
        except Exception as e:
            processor.logger.error(f"Existing processor failed: {e}")
            processor.error_manager.record_error(
                category=ErrorCategory.SYSTEM_ERROR,
                severity=ErrorSeverity.CRITICAL,
                sku="SYSTEM",
                message=f"Existing processor failed: {str(e)}",
                suggested_fix="Check system logs and fix underlying issue"
            )
            
            # Return error report instead of crashing
            return processor._generate_failure_report(str(e))
    
    return safe_wrapper

# Demo function
def demo_safe_processing():
    """Demonstrate safe processing with error scenarios"""
    
    # Create test data with various error scenarios
    sales_data = pd.DataFrame({
        'SKU': ['ABC123', 'DEF456', 'ABC123', 'XYZ789', 'GHI999'],
        'Quantity_Sold': [100, 50, 200, 75, 0],  # One zero quantity
        'Sale_Date': pd.to_datetime([
            '2025-01-15', '2025-01-16', '2025-01-20', '2025-01-10', '2025-01-25'
        ])
    })
    
    lots_data = pd.DataFrame({
        'SKU': ['ABC123', 'ABC123', 'DEF456', 'GHI999'],  # Missing XYZ789
        'Lot_ID': ['LOT001', 'LOT002', 'LOT003', 'LOT004'],
        'Received_Date': pd.to_datetime([
            '2025-01-01', '2025-01-10', '2025-01-18', '2025-01-05'  # DEF456 lot after sale
        ]),
        'Original_Unit_Qty': [200, 150, 100, 50],
        'Remaining_Unit_Qty': [200, 150, 100, -10],  # One negative remaining
        'Unit_Price': [10.0, 11.0, 15.0, 8.0],
        'Freight_Cost_Per_Unit': [1.0, 1.0, 2.0, 0.5]
    })
    
    # Process with safe processor
    processor = FIFOSafeProcessor("demo_safe_processing")
    result = processor.process_batch_safely(sales_data, lots_data)
    
    print("Safe Processing Demo Results:")
    print("=" * 50)
    print(f"Status: {result['status']}")
    print(f"SKU Success Rate: {result['success_rate']['skus']:.1f}%")
    print(f"Total Errors: {result['statistics']['total_errors']}")
    
    if result.get('actionable_steps'):
        print("\nActionable Steps:")
        for step in result['actionable_steps']:
            print(f"  {step}")
    
    print(f"\nDetailed reports available in: {processor.output_dir}")

if __name__ == "__main__":
    demo_safe_processing()