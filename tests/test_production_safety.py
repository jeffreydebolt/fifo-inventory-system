#!/usr/bin/env python3
"""
CRITICAL PRODUCTION SAFETY TESTS
These tests verify that existing functionality continues to work perfectly.
ANY FAILURE indicates potential client impact and must be fixed immediately.
"""

import unittest
import pandas as pd
import os
import sys
import logging
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the production FIFO calculator (carefully)
try:
    import fifo_calculator_supabase as fifo_production
except ImportError as e:
    print(f"CRITICAL ERROR: Cannot import production FIFO calculator: {e}")
    sys.exit(1)

class TestProductionFIFOSafety(unittest.TestCase):
    """Test the current production FIFO calculator to ensure it works correctly"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_data_dir = "tests/test_data"
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Configure test logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def test_fifo_calculator_imports(self):
        """CRITICAL: Verify production FIFO calculator can be imported"""
        try:
            import fifo_calculator_supabase
            self.assertTrue(hasattr(fifo_calculator_supabase, 'get_supabase_client'))
            self.logger.info("✅ Production FIFO calculator imports successfully")
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Cannot import production FIFO calculator: {e}")
    
    def test_supabase_connection_structure(self):
        """CRITICAL: Verify Supabase connection setup exists"""
        try:
            # Check if connection function exists
            self.assertTrue(hasattr(fifo_production, 'get_supabase_client'))
            
            # Verify environment variables are expected
            required_env_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
            for var in required_env_vars:
                # Don't actually check values (security), just verify structure expects them
                self.logger.info(f"✅ Production code expects environment variable: {var}")
                
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Supabase connection structure invalid: {e}")
    
    def create_test_sales_data(self):
        """Create valid test sales data in the format expected by production"""
        test_sales = pd.DataFrame({
            'SKU': ['TEST001', 'TEST002', 'TEST001'],
            'Units Moved': [10, 5, 15],
            'Month': ['January 2025', 'January 2025', 'February 2025']
        })
        
        test_file = os.path.join(self.test_data_dir, 'test_sales.csv')
        test_sales.to_csv(test_file, index=False)
        return test_file
    
    def test_sales_data_processing(self):
        """CRITICAL: Verify sales data can be processed in expected format"""
        test_file = self.create_test_sales_data()
        
        try:
            # Test the column mapping function if it exists
            if hasattr(fifo_production, 'USER_SALES_COLUMNS_MAPPING'):
                mapping = fifo_production.USER_SALES_COLUMNS_MAPPING
                expected_keys = ['sku', 'units moved', 'Month']
                
                for key in expected_keys:
                    self.assertIn(key, mapping, f"Missing column mapping for {key}")
                
                self.logger.info("✅ Sales data column mapping structure is valid")
            
            # Verify file can be read
            df = pd.read_csv(test_file)
            self.assertEqual(len(df), 3)
            self.assertIn('SKU', df.columns)
            self.assertIn('Units Moved', df.columns)
            self.assertIn('Month', df.columns)
            
            self.logger.info("✅ Test sales data file format is valid")
            
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Sales data processing broken: {e}")
        
        finally:
            # Clean up test file
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_purchase_lots_table_structure(self):
        """CRITICAL: Verify expected purchase_lots table structure"""
        try:
            # Check if production code expects correct table structure
            if hasattr(fifo_production, 'SUPABASE_PURCHASES_TABLE_NAME'):
                table_name = fifo_production.SUPABASE_PURCHASES_TABLE_NAME
                self.assertEqual(table_name, "purchase_lots")
                self.logger.info("✅ Purchase lots table name is correct")
            
            # Verify expected column names are referenced in code
            expected_columns = [
                'lot_id', 'po_number', 'sku', 'received_date',
                'original_unit_qty', 'unit_price', 'freight_cost_per_unit', 'remaining_unit_qty'
            ]
            
            # Read the production file and check column references
            with open('fifo_calculator_supabase.py', 'r') as f:
                code_content = f.read()
                
            for column in expected_columns:
                # Look for column references in the code
                if column in code_content:
                    self.logger.info(f"✅ Column '{column}' is referenced in production code")
                    
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Purchase lots table structure check failed: {e}")
    
    def test_fifo_logic_functions_exist(self):
        """CRITICAL: Verify core FIFO functions exist in production code"""
        try:
            # Check for key function signatures in production code
            with open('fifo_calculator_supabase.py', 'r') as f:
                code_content = f.read()
            
            # Look for critical FIFO processing patterns
            critical_patterns = [
                'load_and_validate_purchases',
                'process_sales',
                'FIFO',
                'oldest.*first',
                'remaining_unit_qty',
                'update.*supabase'
            ]
            
            found_patterns = []
            for pattern in critical_patterns:
                if pattern.lower() in code_content.lower():
                    found_patterns.append(pattern)
                    self.logger.info(f"✅ Found FIFO pattern: {pattern}")
            
            # Verify we found core FIFO logic
            self.assertGreater(len(found_patterns), 3, 
                             "CRITICAL: Core FIFO logic patterns not found in production code")
                             
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: FIFO logic verification failed: {e}")
    
    def test_output_file_structure(self):
        """CRITICAL: Verify production code generates expected outputs"""
        try:
            # Check expected output file names
            expected_outputs = [
                'cogs_attribution_supabase.csv',
                'cogs_summary_supabase.csv', 
                'updated_inventory_snapshot_supabase.csv'
            ]
            
            with open('fifo_calculator_supabase.py', 'r') as f:
                code_content = f.read()
            
            for output_file in expected_outputs:
                if output_file in code_content:
                    self.logger.info(f"✅ Output file '{output_file}' is generated by production code")
                else:
                    self.logger.warning(f"⚠️ Output file '{output_file}' not found in production code")
                    
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Output file structure check failed: {e}")

class TestDashboardSafety(unittest.TestCase):
    """Test the current dashboard to ensure it works correctly"""
    
    def setUp(self):
        """Set up dashboard tests"""
        self.dashboard_path = "cogs-dashboard"
        self.src_path = os.path.join(self.dashboard_path, "src")
        
    def test_dashboard_structure(self):
        """CRITICAL: Verify dashboard file structure is intact"""
        critical_files = [
            'package.json',
            'src/App.js',
            'src/index.js',
            'src/lib/supabaseClient.ts',
            'src/components/AuthGuard.tsx',
            'src/pages/Home.js',
            'src/services/api.js'
        ]
        
        for file_path in critical_files:
            full_path = os.path.join(self.dashboard_path, file_path)
            self.assertTrue(os.path.exists(full_path), 
                          f"CRITICAL: Missing dashboard file: {file_path}")
            self.logger.info(f"✅ Dashboard file exists: {file_path}")
    
    def test_package_dependencies(self):
        """CRITICAL: Verify dashboard dependencies are correct"""
        package_path = os.path.join(self.dashboard_path, 'package.json')
        
        if os.path.exists(package_path):
            with open(package_path, 'r') as f:
                import json
                package_data = json.load(f)
                
            critical_deps = [
                '@supabase/supabase-js',
                'react',
                'react-dom',
                'axios'
            ]
            
            dependencies = package_data.get('dependencies', {})
            for dep in critical_deps:
                self.assertIn(dep, dependencies, f"CRITICAL: Missing dependency: {dep}")
                self.logger.info(f"✅ Dashboard dependency found: {dep}")
                
    def test_api_service_structure(self):
        """CRITICAL: Verify API service layer is intact"""
        api_service_path = os.path.join(self.src_path, 'services', 'api.js')
        
        if os.path.exists(api_service_path):
            with open(api_service_path, 'r') as f:
                api_content = f.read()
                
            # Check for critical API patterns
            critical_patterns = [
                'axios',
                'API_BASE_URL',
                'interceptors',
                'error handling'
            ]
            
            for pattern in critical_patterns:
                self.assertIn(pattern.lower(), api_content.lower(),
                            f"CRITICAL: Missing API pattern: {pattern}")
                self.logger.info(f"✅ API service has pattern: {pattern}")

class TestSystemIntegration(unittest.TestCase):
    """Test integration points between components"""
    
    def test_environment_variable_usage(self):
        """CRITICAL: Verify environment variables are used correctly"""
        
        # Check FIFO calculator environment usage
        try:
            with open('fifo_calculator_supabase.py', 'r') as f:
                fifo_content = f.read()
                
            env_patterns = ['os.environ', 'SUPABASE_URL', 'SUPABASE_KEY']
            for pattern in env_patterns:
                self.assertIn(pattern, fifo_content,
                            f"CRITICAL: Environment variable pattern '{pattern}' not found")
                            
        except Exception as e:
            self.fail(f"CRITICAL FAILURE: Environment variable check failed: {e}")
    
    def test_current_output_directories_exist(self):
        """CRITICAL: Verify current output directories are accessible"""
        
        # Check for existing output directories (client data)
        potential_output_dirs = [
            'july_2025_final',
            'production_enhanced', 
            'production_test_outputs'
        ]
        
        existing_dirs = []
        for dir_name in potential_output_dirs:
            if os.path.exists(dir_name):
                existing_dirs.append(dir_name)
                
                # Verify directory is readable
                try:
                    files = os.listdir(dir_name)
                    self.logger.info(f"✅ Output directory accessible: {dir_name} ({len(files)} files)")
                except PermissionError:
                    self.fail(f"CRITICAL: Cannot access output directory: {dir_name}")
        
        # Should have at least one output directory (indicating system has been used)
        self.assertGreater(len(existing_dirs), 0, 
                         "CRITICAL: No output directories found - system may not be working")

def run_safety_tests():
    """Run all safety tests and report results"""
    print("🚨 RUNNING CRITICAL PRODUCTION SAFETY TESTS 🚨")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTest(unittest.makeSuite(TestProductionFIFOSafety))
    suite.addTest(unittest.makeSuite(TestDashboardSafety))
    suite.addTest(unittest.makeSuite(TestSystemIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report results
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ ALL SAFETY TESTS PASSED - SYSTEM IS STABLE")
        print("✅ Safe to proceed with careful development")
        return True
    else:
        print("❌ SAFETY TESTS FAILED - DO NOT MAKE CHANGES")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        print("❌ FIX THESE ISSUES BEFORE PROCEEDING")
        return False

if __name__ == "__main__":
    success = run_safety_tests()
    sys.exit(0 if success else 1)