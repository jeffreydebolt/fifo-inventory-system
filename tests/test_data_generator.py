"""
Test data generator for comprehensive FIFO testing.
Creates realistic sales data, purchase lots, and edge cases for validation.
"""
import pandas as pd
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import csv
import os


class TestDataGenerator:
    """Generates test data for FIFO calculator validation"""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible tests"""
        random.seed(seed)
        
        # Common SKU patterns based on existing data
        self.sku_prefixes = ['1GLBD', '2GLBD', '3GLBD', '4GLBD', '5GLBD', 
                            '1TCST', '2TCST', '1WTCST', '2LSB', '34CSK']
        self.sku_suffixes = ['10354', '10310', '1713B', '1713', '151210', 
                            '11055', '16104', '1261BH', '1925', '8104']
    
    def generate_skus(self, count: int) -> List[str]:
        """Generate realistic SKU patterns"""
        skus = []
        for _ in range(count):
            prefix = random.choice(self.sku_prefixes)
            suffix = random.choice(self.sku_suffixes)
            # Add some random digits to make unique
            extra = str(random.randint(10, 99))
            skus.append(f"{prefix}{suffix}{extra}")
        return list(set(skus))  # Remove duplicates
    
    def generate_purchase_lots(self, 
                             skus: List[str], 
                             start_date: datetime, 
                             end_date: datetime,
                             lots_per_sku: int = 3) -> pd.DataFrame:
        """Generate realistic purchase lot data"""
        lots = []
        lot_id_counter = 1
        
        for sku in skus:
            for _ in range(lots_per_sku):
                # Random date within range
                days_range = (end_date - start_date).days
                received_date = start_date + timedelta(days=random.randint(0, days_range))
                
                # Realistic quantities and prices
                original_qty = random.choice([50, 100, 200, 500, 1000])
                remaining_qty = random.randint(0, original_qty)  # Some lots may be depleted
                
                # Price ranges based on SKU type
                if sku.startswith('1GLBD'):
                    unit_price = round(random.uniform(8.0, 15.0), 2)
                    freight_cost = round(random.uniform(0.5, 2.0), 2)
                elif sku.startswith('2GLBD'):
                    unit_price = round(random.uniform(12.0, 20.0), 2)
                    freight_cost = round(random.uniform(1.0, 3.0), 2)
                else:
                    unit_price = round(random.uniform(5.0, 25.0), 2)
                    freight_cost = round(random.uniform(0.3, 1.5), 2)
                
                lots.append({
                    'lot_id': f'LOT{lot_id_counter:06d}',
                    'po_number': f'PO{random.randint(10000, 99999)}',
                    'sku': sku,
                    'received_date': received_date.strftime('%Y-%m-%d'),
                    'original_unit_qty': original_qty,
                    'unit_price': unit_price,
                    'freight_cost_per_unit': freight_cost,
                    'remaining_unit_qty': remaining_qty
                })
                lot_id_counter += 1
        
        return pd.DataFrame(lots)
    
    def generate_sales_data(self,
                           skus: List[str],
                           start_date: datetime,
                           end_date: datetime,
                           transactions_per_month: int = 100) -> pd.DataFrame:
        """Generate realistic sales transaction data"""
        sales = []
        sale_id_counter = 1
        
        # Generate sales for each month in range
        current_date = start_date
        while current_date <= end_date:
            month_str = current_date.strftime('%B %Y')
            
            # Generate transactions for this month
            for _ in range(transactions_per_month):
                sku = random.choice(skus)
                quantity = random.choice([1, 2, 3, 5, 10, 15, 20, 25, 50, 100])
                
                # Add some returns (negative quantities)
                if random.random() < 0.05:  # 5% chance of return
                    quantity = -random.randint(1, 10)
                
                sales.append({
                    'sale_id': f'SALE{sale_id_counter:06d}',
                    'sku': sku,
                    'units moved': quantity,
                    'Month': month_str,
                    'sale_date': current_date.strftime('%Y-%m-%d')
                })
                sale_id_counter += 1
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return pd.DataFrame(sales)
    
    def generate_edge_case_scenarios(self) -> Dict[str, pd.DataFrame]:
        """Generate specific edge case test scenarios"""
        scenarios = {}
        
        # Scenario 1: Insufficient inventory
        scenarios['insufficient_inventory'] = self._create_insufficient_inventory_scenario()
        
        # Scenario 2: Sales before inventory received
        scenarios['sales_before_inventory'] = self._create_sales_before_inventory_scenario()
        
        # Scenario 3: Complex multi-lot allocation
        scenarios['complex_allocation'] = self._create_complex_allocation_scenario()
        
        # Scenario 4: Returns scenario
        scenarios['returns_processing'] = self._create_returns_scenario()
        
        # Scenario 5: Date edge cases
        scenarios['date_edge_cases'] = self._create_date_edge_cases()
        
        return scenarios
    
    def _create_insufficient_inventory_scenario(self) -> Dict[str, pd.DataFrame]:
        """Test scenario with insufficient inventory"""
        sku = 'TEST_SKU_001'
        
        # Create minimal inventory
        lots = pd.DataFrame([{
            'lot_id': 'LOT_TEST_001',
            'po_number': 'PO_TEST_001',
            'sku': sku,
            'received_date': '2024-01-01',
            'original_unit_qty': 50,
            'unit_price': 10.0,
            'freight_cost_per_unit': 1.0,
            'remaining_unit_qty': 50
        }])
        
        # Try to sell more than available
        sales = pd.DataFrame([{
            'sale_id': 'SALE_TEST_001',
            'sku': sku,
            'units moved': 100,  # More than the 50 available
            'Month': 'February 2024',
            'sale_date': '2024-02-01'
        }])
        
        return {'lots': lots, 'sales': sales}
    
    def _create_sales_before_inventory_scenario(self) -> Dict[str, pd.DataFrame]:
        """Test scenario with sales before inventory received"""
        sku = 'TEST_SKU_002'
        
        # Inventory received later
        lots = pd.DataFrame([{
            'lot_id': 'LOT_TEST_002',
            'po_number': 'PO_TEST_002',
            'sku': sku,
            'received_date': '2024-02-01',  # Received after sale
            'original_unit_qty': 100,
            'unit_price': 12.0,
            'freight_cost_per_unit': 1.5,
            'remaining_unit_qty': 100
        }])
        
        # Sale before inventory received
        sales = pd.DataFrame([{
            'sale_id': 'SALE_TEST_002',
            'sku': sku,
            'units moved': 25,
            'Month': 'January 2024',
            'sale_date': '2024-01-15'  # Before inventory received
        }])
        
        return {'lots': lots, 'sales': sales}
    
    def _create_complex_allocation_scenario(self) -> Dict[str, pd.DataFrame]:
        """Test scenario requiring allocation from multiple lots"""
        sku = 'TEST_SKU_003'
        
        # Multiple lots with different costs
        lots = pd.DataFrame([
            {
                'lot_id': 'LOT_TEST_003A',
                'po_number': 'PO_TEST_003A',
                'sku': sku,
                'received_date': '2024-01-01',
                'original_unit_qty': 50,
                'unit_price': 10.0,
                'freight_cost_per_unit': 1.0,
                'remaining_unit_qty': 30  # Partially used
            },
            {
                'lot_id': 'LOT_TEST_003B',
                'po_number': 'PO_TEST_003B',
                'sku': sku,
                'received_date': '2024-01-15',
                'original_unit_qty': 100,
                'unit_price': 12.0,
                'freight_cost_per_unit': 1.2,
                'remaining_unit_qty': 100
            },
            {
                'lot_id': 'LOT_TEST_003C',
                'po_number': 'PO_TEST_003C',
                'sku': sku,
                'received_date': '2024-02-01',
                'original_unit_qty': 75,
                'unit_price': 11.0,
                'freight_cost_per_unit': 1.1,
                'remaining_unit_qty': 75
            }
        ])
        
        # Sale that spans multiple lots
        sales = pd.DataFrame([{
            'sale_id': 'SALE_TEST_003',
            'sku': sku,
            'units moved': 150,  # Will require allocation from multiple lots
            'Month': 'March 2024',
            'sale_date': '2024-03-01'
        }])
        
        return {'lots': lots, 'sales': sales}
    
    def _create_returns_scenario(self) -> Dict[str, pd.DataFrame]:
        """Test scenario with returns"""
        sku = 'TEST_SKU_004'
        
        lots = pd.DataFrame([{
            'lot_id': 'LOT_TEST_004',
            'po_number': 'PO_TEST_004',
            'sku': sku,
            'received_date': '2024-01-01',
            'original_unit_qty': 100,
            'unit_price': 15.0,
            'freight_cost_per_unit': 2.0,
            'remaining_unit_qty': 100
        }])
        
        # Sale followed by partial return
        sales = pd.DataFrame([
            {
                'sale_id': 'SALE_TEST_004A',
                'sku': sku,
                'units moved': 50,
                'Month': 'February 2024',
                'sale_date': '2024-02-01'
            },
            {
                'sale_id': 'RETURN_TEST_004A',
                'sku': sku,
                'units moved': -10,  # Return 10 units
                'Month': 'February 2024',
                'sale_date': '2024-02-15'
            },
            {
                'sale_id': 'SALE_TEST_004B',
                'sku': sku,
                'units moved': 30,
                'Month': 'March 2024',
                'sale_date': '2024-03-01'
            }
        ])
        
        return {'lots': lots, 'sales': sales}
    
    def _create_date_edge_cases(self) -> Dict[str, pd.DataFrame]:
        """Test scenario with date edge cases"""
        sku = 'TEST_SKU_005'
        
        # Lots received on same day but different times
        lots = pd.DataFrame([
            {
                'lot_id': 'LOT_TEST_005A',
                'po_number': 'PO_TEST_005A',
                'sku': sku,
                'received_date': '2024-01-01',
                'original_unit_qty': 50,
                'unit_price': 10.0,
                'freight_cost_per_unit': 1.0,
                'remaining_unit_qty': 50
            },
            {
                'lot_id': 'LOT_TEST_005B',
                'po_number': 'PO_TEST_005B',
                'sku': sku,
                'received_date': '2024-01-01',  # Same date
                'original_unit_qty': 50,
                'unit_price': 11.0,
                'freight_cost_per_unit': 1.1,
                'remaining_unit_qty': 50
            }
        ])
        
        # Sale on exact date of inventory receipt
        sales = pd.DataFrame([{
            'sale_id': 'SALE_TEST_005',
            'sku': sku,
            'units moved': 75,
            'Month': 'January 2024',
            'sale_date': '2024-01-01'  # Same day as lots received
        }])
        
        return {'lots': lots, 'sales': sales}
    
    def save_test_datasets(self, output_dir: str = '/Users/jeffreydebolt/Documents/fifo/tests/test_datasets'):
        """Generate and save all test datasets"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate main test datasets
        skus = self.generate_skus(20)
        
        # Small dataset for quick tests
        small_lots = self.generate_purchase_lots(
            skus[:5], 
            datetime(2024, 1, 1), 
            datetime(2024, 3, 31), 
            lots_per_sku=2
        )
        small_sales = self.generate_sales_data(
            skus[:5], 
            datetime(2024, 2, 1), 
            datetime(2024, 4, 30), 
            transactions_per_month=20
        )
        
        # Medium dataset for comprehensive tests
        medium_lots = self.generate_purchase_lots(
            skus[:15], 
            datetime(2023, 6, 1), 
            datetime(2024, 5, 31), 
            lots_per_sku=4
        )
        medium_sales = self.generate_sales_data(
            skus[:15], 
            datetime(2023, 7, 1), 
            datetime(2024, 6, 30), 
            transactions_per_month=75
        )
        
        # Large dataset for performance tests
        large_lots = self.generate_purchase_lots(
            skus, 
            datetime(2022, 1, 1), 
            datetime(2024, 12, 31), 
            lots_per_sku=6
        )
        large_sales = self.generate_sales_data(
            skus, 
            datetime(2022, 2, 1), 
            datetime(2024, 11, 30), 
            transactions_per_month=150
        )
        
        # Save datasets
        small_lots.to_csv(f'{output_dir}/small_lots.csv', index=False)
        small_sales.to_csv(f'{output_dir}/small_sales.csv', index=False)
        
        medium_lots.to_csv(f'{output_dir}/medium_lots.csv', index=False)
        medium_sales.to_csv(f'{output_dir}/medium_sales.csv', index=False)
        
        large_lots.to_csv(f'{output_dir}/large_lots.csv', index=False)
        large_sales.to_csv(f'{output_dir}/large_sales.csv', index=False)
        
        # Save edge case scenarios
        edge_cases = self.generate_edge_case_scenarios()
        for scenario_name, data in edge_cases.items():
            scenario_dir = f'{output_dir}/edge_cases/{scenario_name}'
            os.makedirs(scenario_dir, exist_ok=True)
            data['lots'].to_csv(f'{scenario_dir}/lots.csv', index=False)
            data['sales'].to_csv(f'{scenario_dir}/sales.csv', index=False)
        
        print(f"Test datasets saved to {output_dir}")
        print(f"Generated datasets:")
        print(f"  - Small: {len(small_lots)} lots, {len(small_sales)} sales")
        print(f"  - Medium: {len(medium_lots)} lots, {len(medium_sales)} sales")
        print(f"  - Large: {len(large_lots)} lots, {len(large_sales)} sales")
        print(f"  - Edge cases: {len(edge_cases)} scenarios")


if __name__ == "__main__":
    generator = TestDataGenerator()
    generator.save_test_datasets()