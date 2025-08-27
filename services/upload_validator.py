"""
Core validation and normalization service for handling messy real-world data formats.
This service never fails completely - it quarantines problematic data and provides clear feedback.
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
import pandas as pd
import numpy as np
import re
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"  # Data cannot be processed
    WARNING = "warning"   # Data can be processed but may need attention
    INFO = "info"        # Informational messages


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    severity: ValidationSeverity
    row_index: int
    column: str
    original_value: Any
    corrected_value: Any = None
    message: str = ""
    action_taken: str = ""


@dataclass
class ValidationResult:
    """Complete validation result with normalized data and issues"""
    normalized_data: pd.DataFrame
    quarantined_data: pd.DataFrame
    issues: List[ValidationIssue] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_critical_issues(self) -> bool:
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)
    
    @property
    def processable_rows(self) -> int:
        return len(self.normalized_data)
    
    @property
    def quarantined_rows(self) -> int:
        return len(self.quarantined_data)


class UploadValidator:
    """
    Intelligent upload validator that handles messy real-world data formats.
    Follows the principle: never lose data, always provide actionable feedback.
    """
    
    # Date patterns for intelligent parsing
    DATE_PATTERNS = [
        (r'^\d{4}-\d{1,2}-\d{1,2}$', '%Y-%m-%d'),         # 2024-07-31
        (r'^\d{1,2}/\d{1,2}/\d{2}$', '%m/%d/%y'),         # 7/5/24
        (r'^\d{1,2}/\d{1,2}/\d{4}$', '%m/%d/%Y'),         # 7/5/2024
        (r'^[A-Za-z]{3}-\d{2}$', '%b-%y'),                # Jul-24
        (r'^[A-Za-z]{3,9}\s+\d{4}$', '%B %Y'),            # July 2024
        (r'^[A-Za-z]{3}\s+\d{4}$', '%b %Y'),              # Jul 2024
        (r'^\d{4}-\d{1,2}$', '%Y-%m'),                    # 2024-07
    ]
    
    # Number cleaning patterns
    NUMBER_PATTERNS = [
        (r'^\$?[\d,]+\.?\d*$', lambda x: x.replace('$', '').replace(',', '')),  # $1,234.56
        (r'^\d+\.?\d*$', lambda x: x),                     # 1234.00
    ]
    
    # SKU normalization patterns  
    SKU_PATTERNS = [
        (r'^SKU:\s*(.+)$', lambda x: re.sub(r'^SKU:\s*', '', x)),  # SKU: ABC-123
        (r'^(.+)\s+(.+)$', lambda x: x.replace(' ', '-')),         # ABC 123 -> ABC-123
    ]
    
    def __init__(self):
        self.issues = []
        
    def validate_sales_data(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate and normalize sales data with comprehensive error handling.
        
        Args:
            df: Raw sales dataframe
            
        Returns:
            ValidationResult with normalized data and issues
        """
        self.issues = []
        original_df = df.copy()
        
        # Initialize result containers
        normalized_rows = []
        quarantined_rows = []
        
        # Clean up the dataframe structure first
        df = self._clean_dataframe_structure(df)
        
        # Detect and map columns
        column_mapping = self._detect_sales_columns(df)
        if not column_mapping or len(column_mapping) < 3:
            return ValidationResult(
                normalized_data=pd.DataFrame(),
                quarantined_data=original_df,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=-1,
                    column="structure",
                    original_value="Unknown",
                    message="Could not identify required columns (SKU, quantity, date)"
                )]
            )
        
        # Process each row individually to avoid losing good data
        for idx, row in df.iterrows():
            try:
                normalized_row = self._validate_sales_row(row, column_mapping, idx)
                if normalized_row is not None:
                    normalized_rows.append(normalized_row)
                else:
                    quarantined_rows.append(original_df.iloc[idx])
            except Exception as e:
                # Log the error but don't fail completely
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=idx,
                    column="row",
                    original_value=str(row.to_dict()),
                    message=f"Unexpected error processing row: {str(e)}"
                ))
                quarantined_rows.append(original_df.iloc[idx])
        
        # Create result dataframes
        if normalized_rows:
            normalized_df = pd.DataFrame(normalized_rows)
        else:
            normalized_df = pd.DataFrame(columns=['sku', 'quantity_sold', 'sale_date', 'sale_id'])
            
        if quarantined_rows:
            quarantined_df = pd.DataFrame(quarantined_rows)
        else:
            quarantined_df = pd.DataFrame()
        
        # Generate summary
        summary = {
            'total_rows': len(original_df),
            'processed_rows': len(normalized_df),
            'quarantined_rows': len(quarantined_df),
            'critical_issues': sum(1 for issue in self.issues if issue.severity == ValidationSeverity.CRITICAL),
            'warnings': sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING),
            'column_mapping': column_mapping
        }
        
        return ValidationResult(
            normalized_data=normalized_df,
            quarantined_data=quarantined_df,
            issues=self.issues.copy(),
            summary=summary
        )
    
    def validate_lots_data(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate and normalize lots data with comprehensive error handling.
        
        Args:
            df: Raw lots dataframe
            
        Returns:
            ValidationResult with normalized data and issues
        """
        self.issues = []
        original_df = df.copy()
        
        # Initialize result containers
        normalized_rows = []
        quarantined_rows = []
        
        # Clean up the dataframe structure first
        df = self._clean_dataframe_structure(df)
        
        # Detect and map columns
        column_mapping = self._detect_lots_columns(df)
        if not column_mapping or len(column_mapping) < 5:
            return ValidationResult(
                normalized_data=pd.DataFrame(),
                quarantined_data=original_df,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=-1,
                    column="structure", 
                    original_value="Unknown",
                    message="Could not identify required columns (lot_id, SKU, received_date, quantities, prices)"
                )]
            )
        
        # Process each row individually
        for idx, row in df.iterrows():
            try:
                normalized_row = self._validate_lots_row(row, column_mapping, idx)
                if normalized_row is not None:
                    normalized_rows.append(normalized_row)
                else:
                    quarantined_rows.append(original_df.iloc[idx])
            except Exception as e:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=idx,
                    column="row",
                    original_value=str(row.to_dict()),
                    message=f"Unexpected error processing row: {str(e)}"
                ))
                quarantined_rows.append(original_df.iloc[idx])
        
        # Create result dataframes
        if normalized_rows:
            normalized_df = pd.DataFrame(normalized_rows)
        else:
            columns = ['lot_id', 'sku', 'received_date', 'original_quantity', 
                      'remaining_quantity', 'unit_price', 'freight_cost_per_unit']
            normalized_df = pd.DataFrame(columns=columns)
            
        if quarantined_rows:
            quarantined_df = pd.DataFrame(quarantined_rows)
        else:
            quarantined_df = pd.DataFrame()
        
        # Generate summary
        summary = {
            'total_rows': len(original_df),
            'processed_rows': len(normalized_df),
            'quarantined_rows': len(quarantined_df),
            'critical_issues': sum(1 for issue in self.issues if issue.severity == ValidationSeverity.CRITICAL),
            'warnings': sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING),
            'column_mapping': column_mapping
        }
        
        return ValidationResult(
            normalized_data=normalized_df,
            quarantined_data=quarantined_df,
            issues=self.issues.copy(),
            summary=summary
        )
    
    def _clean_dataframe_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean up common dataframe structural issues"""
        # Remove completely unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
        
        # Remove trailing empty columns that are just commas in CSV
        for col in df.columns[::-1]:  # Check from right to left
            if df[col].isna().all():
                df = df.drop(columns=[col])
            else:
                break
        
        return df
    
    def _detect_sales_columns(self, df: pd.DataFrame) -> Optional[Dict[str, str]]:
        """Intelligently detect sales data columns"""
        columns = [(col.lower().strip(), col) for col in df.columns]  # (lowercase, original)
        mapping = {}
        
        # SKU patterns
        sku_patterns = ['sku', 'product_sku', 'item_sku', 'part_number', 'product_code', 'item code']
        for pattern in sku_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['sku'] = matches[0]
                break
        
        # Quantity patterns  
        qty_patterns = ['units moved', 'quantity_sold', 'qty', 'quantity', 'units', 'sold', 'volume']
        for pattern in qty_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['quantity'] = matches[0]
                break
        
        # Date patterns
        date_patterns = ['month', 'sale_date', 'date', 'period', 'sales_date', 'sales date']
        for pattern in date_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['date'] = matches[0]
                break
        
        # Must have all three core columns
        if len(mapping) >= 3:
            return mapping
        return None
    
    def _detect_lots_columns(self, df: pd.DataFrame) -> Optional[Dict[str, str]]:
        """Intelligently detect lots data columns"""
        columns = [(col.lower().strip(), col) for col in df.columns]  # (lowercase, original)
        mapping = {}
        
        # Lot ID patterns
        lot_patterns = ['lot_id', 'po_number', 'po number', 'purchase_order', 'lot', 'batch']
        for pattern in lot_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['lot_id'] = matches[0]
                break
        
        # SKU patterns
        sku_patterns = ['sku', 'product_sku', 'product sku', 'item_sku', 'part_number', 'product_code']
        for pattern in sku_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['sku'] = matches[0]
                break
        
        # Date patterns
        date_patterns = ['received_date', 'received date', 'date', 'received', 'purchase_date']
        for pattern in date_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['received_date'] = matches[0]
                break
        
        # Quantity patterns
        orig_qty_patterns = ['original_quantity', 'original_unit_qty', 'original unit qty', 'qty', 'quantity']
        for pattern in orig_qty_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['original_quantity'] = matches[0]
                break
        
        rem_qty_patterns = ['remaining_quantity', 'remaining_unit_qty', 'remaining unit qty', 'remaining']
        for pattern in rem_qty_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['remaining_quantity'] = matches[0]
                break
        
        # Price patterns
        price_patterns = ['unit_price', 'unit price', 'price', 'cost', 'unit cost']
        for pattern in price_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['unit_price'] = matches[0]
                break
        
        # Freight patterns
        freight_patterns = ['freight_cost_per_unit', 'actual_freight_cost_per_unit', 'freight cost', 'freight', 'shipping']
        for pattern in freight_patterns:
            matches = [orig for lower, orig in columns if pattern in lower]
            if matches:
                mapping['freight_cost_per_unit'] = matches[0]
                break
        
        # Must have core columns
        required = ['lot_id', 'sku', 'received_date', 'original_quantity', 'unit_price']
        if all(req in mapping for req in required):
            return mapping
        return None
    
    def _validate_sales_row(self, row: pd.Series, column_mapping: Dict[str, str], idx: int) -> Optional[Dict[str, Any]]:
        """Validate and normalize a single sales row"""
        result = {}
        has_critical_error = False
        
        # Validate SKU
        sku_col = column_mapping.get('sku')
        if sku_col and sku_col in row:
            sku = self._normalize_sku(row[sku_col], idx)
            if sku:
                result['sku'] = sku
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Validate quantity
        qty_col = column_mapping.get('quantity')
        if qty_col and qty_col in row:
            quantity = self._normalize_quantity(row[qty_col], idx, qty_col)
            if quantity is not None:
                result['quantity_sold'] = quantity
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Validate date
        date_col = column_mapping.get('date')
        if date_col and date_col in row:
            date = self._normalize_date(row[date_col], idx, date_col)
            if date:
                result['sale_date'] = date
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Generate sale ID
        result['sale_id'] = f"SALE_{idx}_{int(datetime.now().timestamp())}"
        
        return result if not has_critical_error else None
    
    def _validate_lots_row(self, row: pd.Series, column_mapping: Dict[str, str], idx: int) -> Optional[Dict[str, Any]]:
        """Validate and normalize a single lots row"""
        result = {}
        has_critical_error = False
        
        # Validate lot_id
        lot_col = column_mapping.get('lot_id')
        if lot_col and lot_col in row:
            lot_id = str(row[lot_col]).strip() if pd.notna(row[lot_col]) else None
            if lot_id:
                result['lot_id'] = lot_id
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Validate SKU
        sku_col = column_mapping.get('sku')
        if sku_col and sku_col in row:
            sku = self._normalize_sku(row[sku_col], idx)
            if sku:
                result['sku'] = sku
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Validate received date
        date_col = column_mapping.get('received_date')
        if date_col and date_col in row:
            date = self._normalize_date(row[date_col], idx, date_col)
            if date:
                result['received_date'] = date
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Validate quantities
        orig_qty_col = column_mapping.get('original_quantity')
        if orig_qty_col and orig_qty_col in row:
            qty = self._normalize_quantity(row[orig_qty_col], idx, orig_qty_col)
            if qty is not None and qty > 0:
                result['original_quantity'] = qty
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Remaining quantity (optional, defaults to original)
        rem_qty_col = column_mapping.get('remaining_quantity')
        if rem_qty_col and rem_qty_col in row:
            qty = self._normalize_quantity(row[rem_qty_col], idx, rem_qty_col)
            result['remaining_quantity'] = qty if qty is not None else result.get('original_quantity', 0)
        else:
            result['remaining_quantity'] = result.get('original_quantity', 0)
        
        # Validate unit price
        price_col = column_mapping.get('unit_price')
        if price_col and price_col in row:
            price = self._normalize_currency(row[price_col], idx, price_col)
            if price is not None and price >= 0:
                result['unit_price'] = price
            else:
                has_critical_error = True
        else:
            has_critical_error = True
        
        # Freight cost (optional, defaults to 0)
        freight_col = column_mapping.get('freight_cost_per_unit')
        if freight_col and freight_col in row:
            freight = self._normalize_currency(row[freight_col], idx, freight_col)
            result['freight_cost_per_unit'] = freight if freight is not None else 0.0
        else:
            result['freight_cost_per_unit'] = 0.0
        
        return result if not has_critical_error else None
    
    def _normalize_sku(self, value: Any, row_idx: int) -> Optional[str]:
        """Normalize SKU values with intelligent cleaning"""
        if pd.isna(value) or str(value).strip() == "":
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                row_index=row_idx,
                column="sku",
                original_value=value,
                message="SKU is empty or null"
            ))
            return None
        
        # Convert to string and clean
        sku = str(value).strip().upper()
        
        # Apply SKU normalization patterns
        for pattern, transformer in self.SKU_PATTERNS:
            if re.match(pattern, sku, re.IGNORECASE):
                normalized = transformer(sku)
                if normalized != sku:
                    self.issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        row_index=row_idx,
                        column="sku",
                        original_value=value,
                        corrected_value=normalized,
                        message=f"SKU normalized from '{sku}' to '{normalized}'"
                    ))
                    sku = normalized
                break
        
        return sku
    
    def _normalize_quantity(self, value: Any, row_idx: int, column: str) -> Optional[int]:
        """Normalize quantity values with error handling"""
        if pd.isna(value):
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                row_index=row_idx,
                column=column,
                original_value=value,
                message=f"Quantity is null in column '{column}'"
            ))
            return None
        
        # Handle string representations
        if isinstance(value, str):
            # Remove common non-numeric characters
            cleaned = re.sub(r'[,$\s]', '', value.strip())
            try:
                quantity = float(cleaned)
            except ValueError:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=row_idx,
                    column=column,
                    original_value=value,
                    message=f"Cannot parse quantity '{value}' in column '{column}'"
                ))
                return None
        else:
            try:
                quantity = float(value)
            except (ValueError, TypeError):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=row_idx,
                    column=column,
                    original_value=value,
                    message=f"Cannot convert quantity '{value}' to number in column '{column}'"
                ))
                return None
        
        # Convert to integer
        if quantity != int(quantity):
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                row_index=row_idx,
                column=column,
                original_value=value,
                corrected_value=int(quantity),
                message=f"Quantity rounded from {quantity} to {int(quantity)}"
            ))
        
        return int(quantity)
    
    def _normalize_currency(self, value: Any, row_idx: int, column: str) -> Optional[float]:
        """Normalize currency/price values"""
        if pd.isna(value):
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                row_index=row_idx,
                column=column,
                original_value=value,
                corrected_value=0.0,
                message=f"Price is null in column '{column}', defaulting to 0.0"
            ))
            return 0.0
        
        # Handle string representations
        if isinstance(value, str):
            # Apply number cleaning patterns
            cleaned = value.strip()
            for pattern, cleaner in self.NUMBER_PATTERNS:
                if re.match(pattern, cleaned):
                    cleaned = cleaner(cleaned)
                    break
            
            try:
                price = float(cleaned)
            except ValueError:
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=row_idx,
                    column=column,
                    original_value=value,
                    message=f"Cannot parse price '{value}' in column '{column}'"
                ))
                return None
        else:
            try:
                price = float(value)
            except (ValueError, TypeError):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    row_index=row_idx,
                    column=column,
                    original_value=value,
                    message=f"Cannot convert price '{value}' to number in column '{column}'"
                ))
                return None
        
        return round(price, 2)
    
    def _normalize_date(self, value: Any, row_idx: int, column: str) -> Optional[datetime]:
        """Normalize date values with multiple format support"""
        if pd.isna(value) or str(value).strip() == "":
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                row_index=row_idx,
                column=column,
                original_value=value,
                message=f"Date is empty or null in column '{column}'"
            ))
            return None
        
        date_str = str(value).strip()
        
        # Try each date pattern
        for pattern, date_format in self.DATE_PATTERNS:
            if re.match(pattern, date_str):
                try:
                    parsed_date = datetime.strptime(date_str, date_format)
                    
                    # For month-only dates, use first day of month
                    if date_format in ['%B %Y', '%b %Y', '%Y-%m']:
                        parsed_date = parsed_date.replace(day=1)
                    
                    # Check for future dates
                    if parsed_date > datetime.now():
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            row_index=row_idx,
                            column=column,
                            original_value=value,
                            corrected_value=parsed_date,
                            message=f"Date '{date_str}' is in the future"
                        ))
                    
                    return parsed_date
                except ValueError:
                    continue
        
        # If no pattern matched, try pandas parsing as last resort
        try:
            parsed_date = pd.to_datetime(date_str)
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                row_index=row_idx,
                column=column,
                original_value=value,
                corrected_value=parsed_date,
                message=f"Date '{date_str}' parsed using pandas fallback"
            ))
            return parsed_date.to_pydatetime()
        except:
            pass
        
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.CRITICAL,
            row_index=row_idx,
            column=column,
            original_value=value,
            message=f"Cannot parse date '{date_str}' in column '{column}'"
        ))
        return None