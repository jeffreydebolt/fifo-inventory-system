"""
CSV normalization utilities for handling various date formats and data quality issues.
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any


class CSVNormalizer:
    """Normalizes CSV data for consistent processing"""
    
    MONTH_FORMATS = [
        "%B %Y",      # June 2025
        "%b %Y",      # Jun 2025
        "%Y-%m",      # 2025-06
        "%m/%Y",      # 06/2025
        "%Y/%m",      # 2025/06
    ]
    
    @staticmethod
    def normalize_sales_csv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize sales CSV data with proper error handling.
        
        Args:
            df: Raw dataframe from CSV
            
        Returns:
            Normalized dataframe
            
        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        # Remove unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Standardize column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Check required columns
        required_columns = ['sku', 'units moved', 'month']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            # Try alternative column names
            column_mapping = {
                'quantity_sold': 'units moved',
                'sale_date': 'month',
                'product_sku': 'sku'
            }
            
            for old, new in column_mapping.items():
                if old in df.columns and new in missing_columns:
                    df = df.rename(columns={old: new})
                    missing_columns.remove(new)
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Validate SKU column
        invalid_skus = df[df['sku'].isna() | (df['sku'].astype(str).str.strip() == '')]
        if len(invalid_skus) > 0:
            raise ValueError(f"Found {len(invalid_skus)} rows with invalid SKU values")
        
        # Validate and convert units moved
        df['units moved'] = pd.to_numeric(df['units moved'], errors='coerce')
        invalid_units = df[df['units moved'].isna()]
        if len(invalid_units) > 0:
            raise ValueError(f"Found {len(invalid_units)} rows with non-numeric units moved values")
        
        df['units moved'] = df['units moved'].astype(int)
        
        # Normalize Month/Date column
        df = CSVNormalizer._normalize_dates(df)
        
        return df
    
    @staticmethod
    def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize date columns to consistent format"""
        if 'month' in df.columns:
            # Handle Month column (e.g., "June 2025")
            invalid_months = df[df['month'].isna() | (df['month'].astype(str).str.strip() == '')]
            if len(invalid_months) > 0:
                raise ValueError(f"Found {len(invalid_months)} rows with invalid month values")
            
            # Try to parse with multiple formats
            df['sale_date'] = pd.NaT
            month_str_col = df['month'].astype(str).str.strip()
            
            for fmt in CSVNormalizer.MONTH_FORMATS:
                mask = df['sale_date'].isna()
                try:
                    df.loc[mask, 'sale_date'] = pd.to_datetime(
                        month_str_col[mask], 
                        format=fmt,
                        errors='coerce'
                    )
                except:
                    continue
            
            # For month-only dates, use first day of month
            still_invalid = df[df['sale_date'].isna()]
            if len(still_invalid) > 0:
                raise ValueError(
                    f"Could not parse {len(still_invalid)} date values. "
                    f"Examples: {still_invalid['month'].head().tolist()}"
                )
            
            # Keep original month column for reference
            df = df.rename(columns={'month': 'original_month'})
            
        elif 'sale_date' in df.columns:
            # Already has sale_date column
            df['sale_date'] = pd.to_datetime(df['sale_date'], errors='coerce')
            invalid_dates = df[df['sale_date'].isna()]
            if len(invalid_dates) > 0:
                raise ValueError(f"Found {len(invalid_dates)} rows with invalid sale_date values")
        else:
            raise ValueError("No date column found (expected 'month' or 'sale_date')")
        
        return df
    
    @staticmethod
    def create_sale_objects(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert normalized dataframe to sale objects"""
        sales = []
        
        for idx, row in df.iterrows():
            sale = {
                'sale_id': str(row.get('sale_id', f"SALE_{idx}")),
                'sku': str(row['sku']),
                'sale_date': row['sale_date'].to_pydatetime(),
                'quantity_sold': int(row['units moved'])
            }
            sales.append(sale)
        
        return sales