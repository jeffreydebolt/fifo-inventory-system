"""
Intelligent format detection service for identifying data formats and structures
in uploaded CSV files before validation.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class FileType(Enum):
    """Detected file types"""
    SALES_DATA = "sales_data"
    LOTS_DATA = "lots_data" 
    UNKNOWN = "unknown"


class DateFormat(Enum):
    """Detected date formats"""
    MONTH_YEAR = "month_year"        # July 2024, Jul 2024
    FULL_DATE = "full_date"          # 2024-07-31, 7/5/24
    MONTH_ONLY = "month_only"        # 2024-07
    MIXED = "mixed"                  # Multiple formats in same column
    UNKNOWN = "unknown"


class NumberFormat(Enum):
    """Detected number formats"""
    INTEGER = "integer"              # 123
    DECIMAL = "decimal"              # 123.45
    CURRENCY = "currency"            # $123.45, $1,234.56
    SCIENTIFIC = "scientific"        # 1.23E+04
    PERCENTAGE = "percentage"        # 15.5%
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class ColumnInfo:
    """Information about a detected column"""
    name: str
    original_name: str
    data_type: type
    sample_values: List[Any]
    null_count: int
    null_percentage: float
    unique_count: int
    format_type: Optional[Any] = None  # DateFormat, NumberFormat, etc.
    confidence: float = 0.0           # 0-1 confidence in detection
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass 
class FormatDetectionResult:
    """Complete format detection result"""
    file_type: FileType
    confidence: float
    columns: Dict[str, ColumnInfo]
    row_count: int
    issues: List[str]
    recommendations: List[str]
    sample_data: pd.DataFrame


class FormatDetector:
    """
    Intelligent format detector that analyzes CSV structure and content
    to determine the best processing approach.
    """
    
    # Column name patterns for sales data
    SALES_PATTERNS = {
        'sku': [
            r'.*sku.*', r'.*product.*', r'.*item.*', r'.*part.*number.*',
            r'.*product.*code.*', r'.*item.*code.*'
        ],
        'quantity': [
            r'.*units.*moved.*', r'.*quantity.*sold.*', r'.*qty.*', r'.*quantity.*',
            r'.*units.*', r'.*sold.*', r'.*volume.*'
        ],
        'date': [
            r'.*month.*', r'.*date.*', r'.*period.*', r'.*sales.*date.*',
            r'.*transaction.*date.*', r'.*sale.*date.*'
        ]
    }
    
    # Column name patterns for lots data
    LOTS_PATTERNS = {
        'lot_id': [
            r'.*lot.*id.*', r'.*po.*number.*', r'.*purchase.*order.*',
            r'.*lot.*', r'.*batch.*', r'.*po.*'
        ],
        'sku': [
            r'.*sku.*', r'.*product.*', r'.*item.*', r'.*part.*number.*'
        ],
        'received_date': [
            r'.*received.*date.*', r'.*date.*', r'.*received.*', 
            r'.*purchase.*date.*', r'.*delivery.*date.*'
        ],
        'original_quantity': [
            r'.*original.*quantity.*', r'.*original.*unit.*qty.*',
            r'.*qty.*', r'.*quantity.*', r'.*units.*'
        ],
        'remaining_quantity': [
            r'.*remaining.*quantity.*', r'.*remaining.*unit.*qty.*',
            r'.*remaining.*', r'.*balance.*'
        ],
        'unit_price': [
            r'.*unit.*price.*', r'.*price.*', r'.*cost.*', r'.*rate.*'
        ],
        'freight_cost': [
            r'.*freight.*cost.*', r'.*freight.*', r'.*shipping.*cost.*',
            r'.*delivery.*cost.*', r'.*actual.*freight.*'
        ]
    }
    
    def __init__(self):
        self.issues = []
        self.recommendations = []
    
    def detect_format(self, df: pd.DataFrame) -> FormatDetectionResult:
        """
        Analyze dataframe structure and detect the most likely format.
        
        Args:
            df: Raw pandas DataFrame from CSV
            
        Returns:
            FormatDetectionResult with detailed analysis
        """
        self.issues = []
        self.recommendations = []
        
        # Clean up dataframe for analysis
        df_clean = self._clean_for_analysis(df)
        
        # Analyze each column
        columns_info = {}
        for col in df_clean.columns:
            columns_info[col] = self._analyze_column(df_clean[col], col)
        
        # Determine file type
        file_type, type_confidence = self._detect_file_type(columns_info)
        
        # Generate recommendations
        self._generate_recommendations(columns_info, file_type)
        
        # Create sample data (first 5 rows)
        sample_data = df_clean.head(5)
        
        return FormatDetectionResult(
            file_type=file_type,
            confidence=type_confidence,
            columns=columns_info,
            row_count=len(df_clean),
            issues=self.issues.copy(),
            recommendations=self.recommendations.copy(),
            sample_data=sample_data
        )
    
    def suggest_column_mapping(self, detection_result: FormatDetectionResult) -> Dict[str, str]:
        """
        Suggest column mappings based on detection results.
        
        Args:
            detection_result: Result from detect_format()
            
        Returns:
            Dictionary mapping standard names to detected column names
        """
        columns = detection_result.columns
        file_type = detection_result.file_type
        
        if file_type == FileType.SALES_DATA:
            return self._suggest_sales_mapping(columns)
        elif file_type == FileType.LOTS_DATA:
            return self._suggest_lots_mapping(columns)
        else:
            return {}
    
    def _clean_for_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean dataframe for analysis purposes"""
        # Remove completely unnamed columns
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names
        df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
        
        # Remove trailing empty columns
        for col in df.columns[::-1]:
            if df[col].isna().all():
                df = df.drop(columns=[col])
            else:
                break
        
        return df
    
    def _analyze_column(self, series: pd.Series, col_name: str) -> ColumnInfo:
        """Analyze a single column to determine its characteristics"""
        # Basic statistics
        null_count = series.isna().sum()
        null_percentage = null_count / len(series) if len(series) > 0 else 1.0
        unique_count = series.nunique()
        
        # Sample non-null values
        non_null_series = series.dropna()
        sample_values = non_null_series.head(5).tolist() if len(non_null_series) > 0 else []
        
        # Detect data type and format
        data_type, format_type, confidence = self._detect_column_type(non_null_series)
        
        # Column-specific issues
        issues = []
        if null_percentage > 0.5:
            issues.append(f"High null percentage: {null_percentage:.1%}")
        if unique_count == 1:
            issues.append("Column has only one unique value")
        if len(non_null_series) == 0:
            issues.append("Column is completely empty")
        
        return ColumnInfo(
            name=col_name.lower().strip(),
            original_name=col_name,
            data_type=data_type,
            sample_values=sample_values,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            format_type=format_type,
            confidence=confidence,
            issues=issues
        )
    
    def _detect_column_type(self, series: pd.Series) -> Tuple[type, Any, float]:
        """Detect the data type and format of a column"""
        if len(series) == 0:
            return str, None, 0.0
        
        # Try to detect dates first
        date_format, date_confidence = self._detect_date_format(series)
        if date_confidence > 0.7:
            return datetime, date_format, date_confidence
        
        # Try to detect numbers
        number_format, number_confidence = self._detect_number_format(series)
        if number_confidence > 0.7:
            return float, number_format, number_confidence
        
        # Check if it's mostly strings
        string_confidence = self._detect_string_confidence(series)
        
        # Return the most confident detection
        detections = [
            (datetime, date_format, date_confidence),
            (float, number_format, number_confidence), 
            (str, None, string_confidence)
        ]
        
        best_detection = max(detections, key=lambda x: x[2])
        return best_detection
    
    def _detect_date_format(self, series: pd.Series) -> Tuple[DateFormat, float]:
        """Detect date format in a series"""
        sample_size = min(10, len(series))
        sample = series.head(sample_size).astype(str)
        
        format_scores = {
            DateFormat.MONTH_YEAR: 0.0,
            DateFormat.FULL_DATE: 0.0,
            DateFormat.MONTH_ONLY: 0.0,
            DateFormat.MIXED: 0.0
        }
        
        # Date patterns to test
        patterns = {
            DateFormat.MONTH_YEAR: [
                r'^[A-Za-z]{3,9}\s+\d{4}$',  # July 2024, January 2024
                r'^[A-Za-z]{3}\s+\d{4}$',    # Jul 2024, Jan 2024
            ],
            DateFormat.FULL_DATE: [
                r'^\d{4}-\d{1,2}-\d{1,2}$',  # 2024-07-31
                r'^\d{1,2}/\d{1,2}/\d{2,4}$',  # 7/5/24, 7/5/2024
                r'^[A-Za-z]{3}-\d{2}$',      # Jul-24
            ],
            DateFormat.MONTH_ONLY: [
                r'^\d{4}-\d{1,2}$',          # 2024-07
                r'^\d{1,2}/\d{4}$',          # 07/2024
            ]
        }
        
        detected_formats = set()
        
        for value in sample:
            value = str(value).strip()
            for date_format, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.match(pattern, value):
                        format_scores[date_format] += 1
                        detected_formats.add(date_format)
                        break
        
        # Normalize scores
        for fmt in format_scores:
            format_scores[fmt] = format_scores[fmt] / sample_size
        
        # Check for mixed formats
        if len(detected_formats) > 1:
            return DateFormat.MIXED, max(format_scores.values())
        
        # Return best format
        best_format = max(format_scores.items(), key=lambda x: x[1])
        return best_format[0], best_format[1]
    
    def _detect_number_format(self, series: pd.Series) -> Tuple[NumberFormat, float]:
        """Detect number format in a series"""
        sample_size = min(10, len(series))
        sample = series.head(sample_size).astype(str)
        
        format_scores = {
            NumberFormat.INTEGER: 0.0,
            NumberFormat.DECIMAL: 0.0,
            NumberFormat.CURRENCY: 0.0,
            NumberFormat.SCIENTIFIC: 0.0,
            NumberFormat.PERCENTAGE: 0.0
        }
        
        patterns = {
            NumberFormat.CURRENCY: r'^\$?[\d,]+\.?\d*$',      # $1,234.56
            NumberFormat.PERCENTAGE: r'^\d+\.?\d*%$',         # 15.5%
            NumberFormat.SCIENTIFIC: r'^\d+\.?\d*[eE][+-]?\d+$', # 1.23E+04
            NumberFormat.DECIMAL: r'^\d+\.\d+$',              # 123.45
            NumberFormat.INTEGER: r'^\d+$',                   # 123
        }
        
        for value in sample:
            value = str(value).strip()
            for number_format, pattern in patterns.items():
                if re.match(pattern, value):
                    format_scores[number_format] += 1
                    break
        
        # Normalize scores
        for fmt in format_scores:
            format_scores[fmt] = format_scores[fmt] / sample_size
        
        # Return best format
        best_format = max(format_scores.items(), key=lambda x: x[1])
        return best_format[0], best_format[1]
    
    def _detect_string_confidence(self, series: pd.Series) -> float:
        """Calculate confidence that this is a string column"""
        sample_size = min(10, len(series))
        sample = series.head(sample_size)
        
        string_indicators = 0
        
        for value in sample:
            value_str = str(value).strip()
            # Look for string indicators
            if any(char.isalpha() for char in value_str):
                string_indicators += 1
            # Long strings are likely text
            elif len(value_str) > 20:
                string_indicators += 1
        
        return string_indicators / sample_size if sample_size > 0 else 0.0
    
    def _detect_file_type(self, columns_info: Dict[str, ColumnInfo]) -> Tuple[FileType, float]:
        """Determine the most likely file type"""
        sales_score = self._calculate_sales_score(columns_info)
        lots_score = self._calculate_lots_score(columns_info)
        
        if sales_score > lots_score and sales_score > 0.3:
            return FileType.SALES_DATA, sales_score
        elif lots_score > sales_score and lots_score > 0.3:
            return FileType.LOTS_DATA, lots_score
        else:
            return FileType.UNKNOWN, 0.0
    
    def _calculate_sales_score(self, columns_info: Dict[str, ColumnInfo]) -> float:
        """Calculate likelihood this is sales data"""
        score = 0.0
        column_names = [col.name for col in columns_info.values()]
        
        # Check for sales-specific patterns
        for required_field, patterns in self.SALES_PATTERNS.items():
            field_score = 0.0
            for col_name in column_names:
                for pattern in patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        field_score = max(field_score, 1.0)
                        break
            score += field_score
        
        # Normalize by number of required fields
        score = score / len(self.SALES_PATTERNS)
        
        # Bonus for typical sales data characteristics
        if len(column_names) <= 5:  # Sales data is typically simpler
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_lots_score(self, columns_info: Dict[str, ColumnInfo]) -> float:
        """Calculate likelihood this is lots data"""
        score = 0.0
        column_names = [col.name for col in columns_info.values()]
        
        # Check for lots-specific patterns  
        for required_field, patterns in self.LOTS_PATTERNS.items():
            field_score = 0.0
            for col_name in column_names:
                for pattern in patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        field_score = max(field_score, 1.0)
                        break
            score += field_score
        
        # Normalize by number of required fields
        score = score / len(self.LOTS_PATTERNS)
        
        # Bonus for typical lots data characteristics
        if len(column_names) >= 5:  # Lots data is typically more complex
            score += 0.1
        
        return min(score, 1.0)
    
    def _suggest_sales_mapping(self, columns_info: Dict[str, ColumnInfo]) -> Dict[str, str]:
        """Suggest column mapping for sales data"""
        mapping = {}
        column_names = [(col.name, col.original_name) for col in columns_info.values()]
        
        for standard_field, patterns in self.SALES_PATTERNS.items():
            best_match = None
            best_score = 0.0
            
            for col_name, original_name in column_names:
                for pattern in patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        score = len(re.findall(pattern, col_name, re.IGNORECASE))
                        if score > best_score:
                            best_score = score
                            best_match = original_name
            
            if best_match:
                mapping[standard_field] = best_match
        
        return mapping
    
    def _suggest_lots_mapping(self, columns_info: Dict[str, ColumnInfo]) -> Dict[str, str]:
        """Suggest column mapping for lots data"""
        mapping = {}
        column_names = [(col.name, col.original_name) for col in columns_info.values()]
        
        for standard_field, patterns in self.LOTS_PATTERNS.items():
            best_match = None
            best_score = 0.0
            
            for col_name, original_name in column_names:
                for pattern in patterns:
                    if re.search(pattern, col_name, re.IGNORECASE):
                        score = len(re.findall(pattern, col_name, re.IGNORECASE))
                        if score > best_score:
                            best_score = score
                            best_match = original_name
            
            if best_match:
                mapping[standard_field] = best_match
        
        return mapping
    
    def _generate_recommendations(self, columns_info: Dict[str, ColumnInfo], file_type: FileType):
        """Generate recommendations based on analysis"""
        # Check for common issues
        empty_columns = [col.original_name for col in columns_info.values() if col.null_percentage > 0.9]
        if empty_columns:
            self.recommendations.append(f"Consider removing mostly empty columns: {', '.join(empty_columns)}")
        
        high_null_columns = [col.original_name for col in columns_info.values() if 0.3 < col.null_percentage <= 0.9]
        if high_null_columns:
            self.recommendations.append(f"Review columns with high null rates: {', '.join(high_null_columns)}")
        
        # Format-specific recommendations
        if file_type == FileType.SALES_DATA:
            self.recommendations.append("Detected as sales data - ensure SKU, quantity, and date columns are present")
        elif file_type == FileType.LOTS_DATA:
            self.recommendations.append("Detected as lots data - ensure lot_id, SKU, dates, quantities, and prices are present")
        else:
            self.recommendations.append("Could not determine file type - check column names and data structure")
        
        # Date format recommendations
        date_columns = [col for col in columns_info.values() if col.data_type == datetime]
        if date_columns:
            mixed_date_cols = [col.original_name for col in date_columns if col.format_type == DateFormat.MIXED]
            if mixed_date_cols:
                self.recommendations.append(f"Standardize date formats in columns: {', '.join(mixed_date_cols)}")