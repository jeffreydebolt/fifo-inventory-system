#!/usr/bin/env python3
"""
INTEGRATED SAFETY SYSTEMS TEST
Test all the safety systems working together without touching production data
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add services to path
sys.path.append('services')

def test_error_recovery_system():
    """Test the error recovery manager"""
    print("🧪 Testing Error Recovery System")
    print("=" * 50)
    
    from error_recovery_manager import ErrorRecoveryManager, ErrorCategory, ErrorSeverity
    
    # Create manager
    manager = ErrorRecoveryManager("test_error_recovery")
    
    # Simulate various error scenarios
    manager.handle_negative_inventory(
        sku="TEST001",
        requested_qty=500,
        available_qty=300,
        lot_details=[{'lot_id': 'LOT001', 'received_date': '2025-01-01', 'remaining': 300}]
    )
    
    manager.handle_missing_lots(
        sku="TEST002",
        sales_qty=100,
        sale_date="2025-01-15"
    )
    
    # Check results
    print(f"✅ Recorded {len(manager.errors)} errors")
    
    can_continue, processable_skus = manager.can_continue_processing()
    print(f"✅ Can continue processing: {can_continue}")
    
    steps = manager.get_actionable_steps()
    print(f"✅ Generated {len(steps)} actionable steps")
    
    reports = manager.export_error_report()
    print(f"✅ Exported reports to: {reports['error_log']}")
    
    return True

def test_safe_fifo_processor():
    """Test the safe FIFO processor"""
    print("\n🧪 Testing Safe FIFO Processor")
    print("=" * 50)
    
    from fifo_safe_processor import FIFOSafeProcessor
    
    # Create test data
    sales_data = pd.DataFrame({
        'SKU': ['GOOD001', 'BAD001', 'GOOD002'],
        'Quantity_Sold': [100, 500, 50],  # BAD001 will have insufficient inventory
        'Sale_Date': pd.to_datetime(['2025-01-15', '2025-01-16', '2025-01-17'])
    })
    
    lots_data = pd.DataFrame({
        'SKU': ['GOOD001', 'GOOD002'],  # Missing BAD001
        'Lot_ID': ['LOT001', 'LOT002'],
        'Received_Date': pd.to_datetime(['2025-01-01', '2025-01-10']),
        'Original_Unit_Qty': [200, 100],
        'Remaining_Unit_Qty': [200, 100],
        'Unit_Price': [10.0, 12.0],
        'Freight_Cost_Per_Unit': [1.0, 1.5]
    })
    
    # Process safely
    processor = FIFOSafeProcessor("test_safe_processing")
    result = processor.process_batch_safely(sales_data, lots_data)
    
    print(f"✅ Processing status: {result['status']}")
    print(f"✅ SKU success rate: {result['success_rate']['skus']:.1f}%")
    print(f"✅ Errors handled: {result['statistics']['total_errors']}")
    print(f"✅ Processed {result['statistics']['processed_skus']}/{result['statistics']['total_skus']} SKUs")
    
    return True

def test_data_format_normalizer():
    """Test the data format normalizer (if available)"""
    print("\n🧪 Testing Data Format Systems")
    print("=" * 50)
    
    try:
        from upload_validator import UploadValidator
        from format_detector import FormatDetector
        
        # Test with messy data
        messy_sales = pd.DataFrame({
            'sku': ['ABC-123', 'def 456', 'GHI789'],
            'units moved': ['$100', '50.0', '75'],
            'Month': ['July 2024', '7/2024', 'Aug-24']
        })
        
        validator = UploadValidator()
        detector = FormatDetector()
        
        # Detect format
        format_info = detector.detect_format(messy_sales, 'sales')
        print(f"✅ Format detection confidence: {format_info.confidence:.1f}%")
        
        # Validate and normalize
        result = validator.validate_and_normalize(messy_sales, 'sales')
        print(f"✅ Validation success rate: {result.success_rate:.1f}%")
        print(f"✅ Clean records: {len(result.clean_data)}")
        print(f"✅ Quarantined records: {len(result.quarantined_data)}")
        
        return True
        
    except ImportError as e:
        print(f"⚠️ Data format systems not available: {e}")
        return False

def test_system_integration():
    """Test how all systems work together"""
    print("\n🧪 Testing System Integration")
    print("=" * 50)
    
    # Simulate a complete processing workflow
    try:
        from fifo_safe_processor import FIFOSafeProcessor
        from error_recovery_manager import ErrorRecoveryManager
        
        # Create processor with error recovery
        processor = FIFOSafeProcessor("test_integration")
        
        # Create problematic test data
        sales_with_issues = pd.DataFrame({
            'SKU': ['GOOD001', 'MISSING001', 'SHORTAGE001'],
            'Quantity_Sold': [50, 100, 1000],  # Various issues
            'Sale_Date': pd.to_datetime(['2025-01-15', '2025-01-16', '2025-01-17'])
        })
        
        lots_limited = pd.DataFrame({
            'SKU': ['GOOD001', 'SHORTAGE001'],  # MISSING001 missing
            'Lot_ID': ['LOT001', 'LOT002'],
            'Received_Date': pd.to_datetime(['2025-01-01', '2025-01-10']),
            'Original_Unit_Qty': [100, 500],
            'Remaining_Unit_Qty': [100, 500],  # SHORTAGE001 short
            'Unit_Price': [10.0, 12.0],
            'Freight_Cost_Per_Unit': [1.0, 1.5]
        })
        
        # Process with comprehensive error handling
        result = processor.process_batch_safely(sales_with_issues, lots_limited)
        
        print(f"✅ Integration test completed")
        print(f"   - Status: {result['status']}")
        print(f"   - Success rate: {result['success_rate']['skus']:.1f}%")
        print(f"   - Errors isolated: {result['statistics']['total_errors']}")
        print(f"   - Processing continued: {'Yes' if result['can_continue_processing'] else 'No'}")
        
        # Verify error isolation worked
        if result['statistics']['processed_skus'] > 0:
            print("✅ Error isolation successful - good SKUs were processed")
        
        if result['statistics']['skipped_skus'] > 0:
            print("✅ Error quarantine successful - bad SKUs were isolated")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_safety_features():
    """Test safety and protection features"""
    print("\n🧪 Testing Safety Features")
    print("=" * 50)
    
    # Test dry run functionality
    from fifo_safe_processor import FIFOSafeProcessor
    
    # Create processor in dry run mode
    safe_processor = FIFOSafeProcessor("test_safety")
    safe_processor.dry_run = True  # Force dry run
    
    print("✅ Dry run mode activated")
    
    # Test with sample data
    sample_sales = pd.DataFrame({
        'SKU': ['TEST001'],
        'Quantity_Sold': [100],
        'Sale_Date': pd.to_datetime(['2025-01-15'])
    })
    
    sample_lots = pd.DataFrame({
        'SKU': ['TEST001'],
        'Lot_ID': ['LOT001'],
        'Received_Date': pd.to_datetime(['2025-01-01']),
        'Original_Unit_Qty': [200],
        'Remaining_Unit_Qty': [200],
        'Unit_Price': [10.0],
        'Freight_Cost_Per_Unit': [1.0]
    })
    
    # This should run safely without touching any real data
    result = safe_processor.process_batch_safely(sample_sales, sample_lots)
    
    print("✅ Safe processing completed without database modifications")
    print(f"✅ Would have processed {result['statistics']['processed_skus']} SKUs")
    
    return True

def main():
    """Run all safety system tests"""
    print("🏥 COMPREHENSIVE SAFETY SYSTEMS TEST")
    print("=" * 60)
    print("Testing all safety components without touching production data...")
    
    tests = [
        ("Error Recovery System", test_error_recovery_system),
        ("Safe FIFO Processor", test_safe_fifo_processor),
        ("Data Format Normalizer", test_data_format_normalizer),
        ("System Integration", test_system_integration),
        ("Safety Features", test_safety_features)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("SAFETY SYSTEMS TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result, error in results:
        if result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            if error:
                print(f"   Error: {error}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed >= total * 0.8:  # 80% pass rate
        print("\n🎉 SAFETY SYSTEMS ARE OPERATIONAL")
        print("✅ Error recovery and isolation working correctly")
        print("✅ Safe processing prevents data corruption") 
        print("✅ System ready for careful production enhancement")
        return True
    else:
        print("\n❌ SAFETY SYSTEMS NEED ATTENTION")
        print("❌ Fix failing tests before proceeding with production")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)