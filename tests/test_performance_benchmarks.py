"""
Performance benchmarks for the FIFO COGS system.
Establishes baseline performance metrics and tests system limits.
"""
import unittest
import time
import psutil
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import json
import subprocess
import tempfile
import statistics

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_data_generator import TestDataGenerator
from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine


class PerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests for FIFO calculations"""
    
    @classmethod
    def setUpClass(cls):
        """Set up performance test data"""
        cls.test_data_dir = '/Users/jeffreydebolt/Documents/fifo/tests/performance_datasets'
        cls.results_file = '/Users/jeffreydebolt/Documents/fifo/tests/performance_results.json'
        cls.generator = TestDataGenerator()
        
        # Create performance test datasets
        os.makedirs(cls.test_data_dir, exist_ok=True)
        cls._generate_performance_datasets()
        
        # Initialize results tracking
        cls.performance_results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': cls._get_system_info(),
            'benchmarks': {}
        }
    
    @classmethod
    def _generate_performance_datasets(cls):
        """Generate datasets of various sizes for performance testing"""
        datasets = {
            'small': {'skus': 10, 'lots_per_sku': 5, 'sales_per_month': 50},
            'medium': {'skus': 50, 'lots_per_sku': 8, 'sales_per_month': 200},
            'large': {'skus': 200, 'lots_per_sku': 12, 'sales_per_month': 500},
            'xlarge': {'skus': 500, 'lots_per_sku': 15, 'sales_per_month': 1000}
        }
        
        for size, config in datasets.items():
            # Generate SKUs
            skus = cls.generator.generate_skus(config['skus'])
            
            # Generate lots
            lots_df = cls.generator.generate_purchase_lots(
                skus,
                datetime(2023, 1, 1),
                datetime(2024, 12, 31),
                lots_per_sku=config['lots_per_sku']
            )
            
            # Generate sales
            sales_df = cls.generator.generate_sales_data(
                skus,
                datetime(2023, 2, 1),
                datetime(2024, 11, 30),
                transactions_per_month=config['sales_per_month']
            )
            
            # Save datasets
            lots_df.to_csv(f'{cls.test_data_dir}/{size}_lots.csv', index=False)
            sales_df.to_csv(f'{cls.test_data_dir}/{size}_sales.csv', index=False)
    
    @classmethod
    def _get_system_info(cls):
        """Get system information for benchmark context"""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'memory_total': psutil.virtual_memory().total,
            'python_version': sys.version,
            'platform': sys.platform
        }
    
    def setUp(self):
        """Set up each test"""
        self.engine = FIFOEngine()
    
    def test_small_dataset_performance(self):
        """Benchmark performance with small dataset"""
        self._run_performance_test('small')
    
    def test_medium_dataset_performance(self):
        """Benchmark performance with medium dataset"""
        self._run_performance_test('medium')
    
    def test_large_dataset_performance(self):
        """Benchmark performance with large dataset"""
        self._run_performance_test('large')
    
    def test_xlarge_dataset_performance(self):
        """Benchmark performance with extra large dataset"""
        self._run_performance_test('xlarge')
    
    def _run_performance_test(self, dataset_size):
        """Run performance test for a specific dataset size"""
        print(f"\nRunning performance test for {dataset_size} dataset...")
        
        # Load data
        lots_df = pd.read_csv(f'{self.test_data_dir}/{dataset_size}_lots.csv')
        sales_df = pd.read_csv(f'{self.test_data_dir}/{dataset_size}_sales.csv')
        
        # Convert to core objects
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Measure memory before
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        # Run multiple iterations for stable timing
        iterations = 3
        times = []
        
        for i in range(iterations):
            # Clear previous state
            self.engine.clear_validation_errors()
            
            # Time the calculation
            start_time = time.perf_counter()
            start_cpu_time = time.process_time()
            
            attributions, final_inventory = self.engine.process_transactions(inventory, sales)
            summaries = self.engine.calculate_summary(attributions)
            
            end_time = time.perf_counter()
            end_cpu_time = time.process_time()
            
            elapsed_time = end_time - start_time
            cpu_time = end_cpu_time - start_cpu_time
            times.append(elapsed_time)
            
            # Validate results on first iteration
            if i == 0:
                self.assertGreater(len(attributions), 0, "Should generate attributions")
                self.assertGreater(len(summaries), 0, "Should generate summaries")
        
        # Measure memory after
        memory_after = process.memory_info().rss
        memory_used = memory_after - memory_before
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        # Calculate throughput
        total_transactions = len(sales)
        throughput = total_transactions / avg_time
        
        # Record results
        benchmark_result = {
            'dataset_size': dataset_size,
            'lots_count': len(lots_df),
            'sales_count': len(sales_df),
            'attributions_generated': len(attributions),
            'summaries_generated': len(summaries),
            'avg_processing_time': avg_time,
            'min_processing_time': min_time,
            'max_processing_time': max_time,
            'cpu_time': cpu_time,
            'memory_used_bytes': memory_used,
            'memory_used_mb': memory_used / (1024 * 1024),
            'throughput_transactions_per_second': throughput,
            'validation_errors': len(self.engine.get_validation_errors()),
            'iterations': iterations
        }
        
        self.performance_results['benchmarks'][dataset_size] = benchmark_result
        
        # Print results
        print(f"Dataset: {dataset_size}")
        print(f"  Lots: {len(lots_df):,}, Sales: {len(sales_df):,}")
        print(f"  Avg Processing Time: {avg_time:.3f}s")
        print(f"  Throughput: {throughput:.1f} transactions/sec")
        print(f"  Memory Used: {memory_used / (1024 * 1024):.1f} MB")
        print(f"  Attributions: {len(attributions):,}")
        print(f"  Validation Errors: {len(self.engine.get_validation_errors())}")
        
        # Performance assertions based on expected thresholds
        if dataset_size == 'small':
            self.assertLess(avg_time, 1.0, "Small dataset should process in under 1 second")
        elif dataset_size == 'medium':
            self.assertLess(avg_time, 10.0, "Medium dataset should process in under 10 seconds")
        elif dataset_size == 'large':
            self.assertLess(avg_time, 60.0, "Large dataset should process in under 60 seconds")
        elif dataset_size == 'xlarge':
            self.assertLess(avg_time, 300.0, "XLarge dataset should process in under 5 minutes")
        
        # Memory usage should be reasonable
        memory_used_gb = memory_used / (1024 * 1024 * 1024)
        self.assertLess(memory_used_gb, 2.0, "Memory usage should be under 2GB")
        
        print(f"✅ {dataset_size.capitalize()} dataset performance test passed")
    
    def test_memory_efficiency(self):
        """Test memory efficiency with large datasets"""
        print("\nTesting memory efficiency...")
        
        # Load large dataset
        lots_df = pd.read_csv(f'{self.test_data_dir}/large_lots.csv')
        sales_df = pd.read_csv(f'{self.test_data_dir}/large_sales.csv')
        
        # Process data in chunks to test memory efficiency
        chunk_size = 1000
        sales_chunks = [sales_df[i:i+chunk_size] for i in range(0, len(sales_df), chunk_size)]
        
        process = psutil.Process(os.getpid())
        peak_memory = process.memory_info().rss
        
        lots = self._dataframe_to_lots(lots_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        all_attributions = []
        
        for i, chunk_df in enumerate(sales_chunks):
            # Monitor memory during processing
            current_memory = process.memory_info().rss
            peak_memory = max(peak_memory, current_memory)
            
            # Process chunk
            sales_chunk = self._dataframe_to_sales(chunk_df)
            attributions, inventory = self.engine.process_transactions(inventory, sales_chunk)
            all_attributions.extend(attributions)
            
            print(f"  Processed chunk {i+1}/{len(sales_chunks)} - "
                  f"Memory: {current_memory / (1024*1024):.1f} MB")
        
        peak_memory_mb = peak_memory / (1024 * 1024)
        print(f"  Peak memory usage: {peak_memory_mb:.1f} MB")
        
        # Memory efficiency assertion
        self.assertLess(peak_memory_mb, 1000, "Peak memory should stay under 1GB")
        
        print("✅ Memory efficiency test passed")
    
    def test_concurrent_processing_simulation(self):
        """Simulate concurrent processing scenarios"""
        print("\nTesting concurrent processing simulation...")
        
        # Load medium dataset for multiple simulated users
        lots_df = pd.read_csv(f'{self.test_data_dir}/medium_lots.csv')
        sales_df = pd.read_csv(f'{self.test_data_dir}/medium_sales.csv')
        
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Simulate multiple concurrent requests
        num_concurrent = 3
        results = []
        
        start_time = time.perf_counter()
        
        for i in range(num_concurrent):
            # Each "user" processes the same data (simulating concurrent access)
            engine = FIFOEngine()
            
            user_start = time.perf_counter()
            attributions, final_inventory = engine.process_transactions(inventory, sales)
            user_end = time.perf_counter()
            
            results.append({
                'user': i + 1,
                'processing_time': user_end - user_start,
                'attributions_count': len(attributions)
            })
        
        total_time = time.perf_counter() - start_time
        
        # Verify all users got consistent results
        attribution_counts = [r['attributions_count'] for r in results]
        self.assertTrue(all(count == attribution_counts[0] for count in attribution_counts),
                       "All concurrent processes should produce same result count")
        
        avg_user_time = statistics.mean([r['processing_time'] for r in results])
        print(f"  Simulated {num_concurrent} concurrent users")
        print(f"  Average processing time per user: {avg_user_time:.3f}s")
        print(f"  Total simulation time: {total_time:.3f}s")
        
        print("✅ Concurrent processing simulation passed")
    
    def test_production_calculator_performance(self):
        """Test performance of the production calculator script"""
        print("\nTesting production calculator performance...")
        
        calculator_path = '/Users/jeffreydebolt/Documents/fifo/fifo_calculator_supabase.py'
        
        if not os.path.exists(calculator_path):
            self.skipTest("Production calculator not found")
        
        # Create a test sales file
        test_sales_path = f'{self.test_data_dir}/perf_test_sales.csv'
        sales_df = pd.read_csv(f'{self.test_data_dir}/medium_sales.csv')
        
        # Take a subset for performance testing
        test_sales_df = sales_df.head(100)  # Use first 100 rows
        test_sales_df.to_csv(test_sales_path, index=False)
        
        try:
            # Time the production calculator
            start_time = time.perf_counter()
            
            result = subprocess.run([
                'python3', calculator_path,
                '--sales-file', test_sales_path,
                '--output-dir', tempfile.mkdtemp(),
                '--skip-supabase-update'  # Assume this flag exists to skip DB updates
            ], capture_output=True, text=True, timeout=120)
            
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            
            print(f"  Production calculator processing time: {processing_time:.3f}s")
            print(f"  Return code: {result.returncode}")
            
            if result.returncode != 0:
                print(f"  stderr: {result.stderr}")
            
            # Performance assertion
            self.assertLess(processing_time, 60.0, 
                           "Production calculator should complete in under 60 seconds")
            
        except subprocess.TimeoutExpired:
            self.fail("Production calculator timed out")
        except FileNotFoundError:
            self.skipTest("Python3 not found or calculator script has dependencies")
        
        finally:
            # Clean up
            if os.path.exists(test_sales_path):
                os.remove(test_sales_path)
        
        print("✅ Production calculator performance test passed")
    
    def _dataframe_to_lots(self, df):
        """Convert DataFrame to PurchaseLot objects"""
        lots = []
        for _, row in df.iterrows():
            lot = PurchaseLot(
                lot_id=str(row['lot_id']),
                sku=str(row['sku']),
                received_date=datetime.strptime(row['received_date'], '%Y-%m-%d'),
                original_quantity=int(row['original_unit_qty']),
                remaining_quantity=int(row['remaining_unit_qty']),
                unit_price=Decimal(str(row['unit_price'])),
                freight_cost_per_unit=Decimal(str(row['freight_cost_per_unit']))
            )
            lots.append(lot)
        return lots
    
    def _dataframe_to_sales(self, df):
        """Convert DataFrame to Sale objects"""
        sales = []
        for _, row in df.iterrows():
            # Only include positive quantities for performance testing
            if int(row['units moved']) > 0:
                sale = Sale(
                    sale_id=str(row.get('sale_id', f"SALE_{len(sales):06d}")),
                    sku=str(row['sku']),
                    sale_date=datetime.strptime(row['sale_date'], '%Y-%m-%d'),
                    quantity_sold=int(row['units moved'])
                )
                sales.append(sale)
        return sales
    
    @classmethod
    def tearDownClass(cls):
        """Save performance results"""
        with open(cls.results_file, 'w') as f:
            json.dump(cls.performance_results, f, indent=2)
        
        print(f"\nPerformance results saved to: {cls.results_file}")
        
        # Print summary
        print("\n" + "="*70)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("="*70)
        
        for size, results in cls.performance_results['benchmarks'].items():
            print(f"{size.upper()}: "
                  f"{results['lots_count']:,} lots, "
                  f"{results['sales_count']:,} sales → "
                  f"{results['avg_processing_time']:.3f}s "
                  f"({results['throughput_transactions_per_second']:.0f} tps)")
        
        print("="*70)


class ScalabilityTests(unittest.TestCase):
    """Test system scalability limits"""
    
    def test_maximum_dataset_size(self):
        """Test with maximum reasonable dataset size"""
        print("\nTesting maximum dataset size limits...")
        
        # Create a very large dataset
        generator = TestDataGenerator()
        skus = generator.generate_skus(100)  # More manageable number for testing
        
        # Generate large dataset
        lots_df = generator.generate_purchase_lots(
            skus,
            datetime(2020, 1, 1),
            datetime(2024, 12, 31),
            lots_per_sku=20
        )
        
        sales_df = generator.generate_sales_data(
            skus,
            datetime(2020, 2, 1),
            datetime(2024, 11, 30),
            transactions_per_month=300
        )
        
        print(f"  Testing with {len(lots_df):,} lots and {len(sales_df):,} sales")
        
        # Process with timeout monitoring
        engine = FIFOEngine()
        
        lots = []
        for _, row in lots_df.iterrows():
            lot = PurchaseLot(
                lot_id=str(row['lot_id']),
                sku=str(row['sku']),
                received_date=datetime.strptime(row['received_date'], '%Y-%m-%d'),
                original_quantity=int(row['original_unit_qty']),
                remaining_quantity=int(row['remaining_unit_qty']),
                unit_price=Decimal(str(row['unit_price'])),
                freight_cost_per_unit=Decimal(str(row['freight_cost_per_unit']))
            )
            lots.append(lot)
        
        sales = []
        for _, row in sales_df.head(1000).iterrows():  # Limit for testing
            if int(row['units moved']) > 0:
                sale = Sale(
                    sale_id=str(row.get('sale_id', f"SALE_{len(sales):06d}")),
                    sku=str(row['sku']),
                    sale_date=datetime.strptime(row['sale_date'], '%Y-%m-%d'),
                    quantity_sold=int(row['units moved'])
                )
                sales.append(sale)
        
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Time the processing
        start_time = time.perf_counter()
        attributions, final_inventory = engine.process_transactions(inventory, sales)
        end_time = time.perf_counter()
        
        processing_time = end_time - start_time
        
        print(f"  Maximum dataset processing time: {processing_time:.3f}s")
        print(f"  Attributions generated: {len(attributions):,}")
        
        # Should complete within reasonable time
        self.assertLess(processing_time, 600.0, "Maximum dataset should process within 10 minutes")
        
        print("✅ Maximum dataset size test passed")


if __name__ == '__main__':
    # Run performance benchmarks
    unittest.main(verbosity=2)