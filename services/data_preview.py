"""
Data preview system that provides users with clear visibility into what will be imported
before any data changes are made to the system.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .upload_validator import ValidationResult, ValidationIssue, ValidationSeverity
from .format_detector import FormatDetectionResult, FileType


class PreviewStatus(Enum):
    """Status of the preview"""
    READY_TO_IMPORT = "ready_to_import"
    NEEDS_REVIEW = "needs_review"
    CANNOT_IMPORT = "cannot_import"


@dataclass
class DataPreview:
    """Complete data preview with import readiness assessment"""
    status: PreviewStatus
    file_type: FileType
    summary: Dict[str, Any]
    normalized_sample: pd.DataFrame
    quarantined_sample: pd.DataFrame
    issues_by_severity: Dict[str, List[ValidationIssue]]
    recommendations: List[str]
    import_plan: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_safe_to_import(self) -> bool:
        """Check if data is safe to import without review"""
        return (self.status == PreviewStatus.READY_TO_IMPORT and 
                len(self.issues_by_severity.get('critical', [])) == 0)
    
    @property
    def requires_manual_review(self) -> bool:
        """Check if data requires manual review before import"""
        return self.status == PreviewStatus.NEEDS_REVIEW
    
    @property
    def cannot_import(self) -> bool:
        """Check if data cannot be imported at all"""
        return self.status == PreviewStatus.CANNOT_IMPORT


class DataPreviewService:
    """
    Service that creates comprehensive data previews showing users exactly
    what will happen when they import their data.
    """
    
    def __init__(self):
        self.max_sample_rows = 10  # Number of rows to show in preview
    
    def create_preview(
        self, 
        detection_result: FormatDetectionResult,
        validation_result: ValidationResult,
        original_filename: str = "uploaded_file.csv"
    ) -> DataPreview:
        """
        Create a comprehensive data preview.
        
        Args:
            detection_result: Format detection results
            validation_result: Validation results
            original_filename: Original filename for context
            
        Returns:
            DataPreview with complete analysis
        """
        # Determine preview status
        status = self._determine_status(validation_result)
        
        # Group issues by severity
        issues_by_severity = self._group_issues_by_severity(validation_result.issues)
        
        # Create summary statistics
        summary = self._create_summary(detection_result, validation_result, original_filename)
        
        # Create sample data for preview
        normalized_sample = self._create_sample_data(validation_result.normalized_data, "normalized")
        quarantined_sample = self._create_sample_data(validation_result.quarantined_data, "quarantined")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(detection_result, validation_result)
        
        # Create import plan
        import_plan = self._create_import_plan(validation_result)
        
        # Generate warnings
        warnings = self._generate_warnings(validation_result)
        
        return DataPreview(
            status=status,
            file_type=detection_result.file_type,
            summary=summary,
            normalized_sample=normalized_sample,
            quarantined_sample=quarantined_sample,
            issues_by_severity=issues_by_severity,
            recommendations=recommendations,
            import_plan=import_plan,
            warnings=warnings
        )
    
    def generate_preview_report(self, preview: DataPreview) -> str:
        """
        Generate a human-readable preview report.
        
        Args:
            preview: DataPreview object
            
        Returns:
            Formatted string report
        """
        report = []
        report.append("=" * 60)
        report.append("DATA IMPORT PREVIEW REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Status section
        report.append(f"STATUS: {preview.status.value.upper()}")
        if preview.status == PreviewStatus.READY_TO_IMPORT:
            report.append("✅ Data is ready to import")
        elif preview.status == PreviewStatus.NEEDS_REVIEW:
            report.append("⚠️  Data needs review before import")
        else:
            report.append("❌ Data cannot be imported")
        report.append("")
        
        # Summary section
        report.append("SUMMARY:")
        report.append(f"  File Type: {preview.file_type.value}")
        report.append(f"  Total Rows: {preview.summary.get('total_rows', 0)}")
        report.append(f"  Processable Rows: {preview.summary.get('processable_rows', 0)}")
        report.append(f"  Quarantined Rows: {preview.summary.get('quarantined_rows', 0)}")
        report.append(f"  Success Rate: {preview.summary.get('success_rate', 0):.1%}")
        report.append("")
        
        # Issues section
        if preview.issues_by_severity:
            report.append("ISSUES FOUND:")
            for severity, issues in preview.issues_by_severity.items():
                if issues:
                    report.append(f"  {severity.upper()}: {len(issues)}")
                    for issue in issues[:3]:  # Show first 3 issues per severity
                        report.append(f"    - Row {issue.row_index}: {issue.message}")
                    if len(issues) > 3:
                        report.append(f"    ... and {len(issues) - 3} more")
            report.append("")
        
        # Sample data section
        if not preview.normalized_sample.empty:
            report.append("SAMPLE OF DATA TO BE IMPORTED:")
            report.append(preview.normalized_sample.to_string(index=False))
            report.append("")
        
        if not preview.quarantined_sample.empty:
            report.append("SAMPLE OF QUARANTINED DATA:")
            report.append(preview.quarantined_sample.to_string(index=False))
            report.append("")
        
        # Warnings section
        if preview.warnings:
            report.append("WARNINGS:")
            for warning in preview.warnings:
                report.append(f"  ⚠️  {warning}")
            report.append("")
        
        # Recommendations section
        if preview.recommendations:
            report.append("RECOMMENDATIONS:")
            for i, rec in enumerate(preview.recommendations, 1):
                report.append(f"  {i}. {rec}")
            report.append("")
        
        # Import plan section
        report.append("IMPORT PLAN:")
        plan = preview.import_plan
        if plan.get('will_import'):
            report.append(f"  ✅ Will import {plan.get('import_count', 0)} rows")
            if plan.get('data_transformations'):
                report.append("  🔧 Data transformations:")
                for transform in plan['data_transformations']:
                    report.append(f"    - {transform}")
        else:
            report.append("  ❌ No data will be imported")
        
        if plan.get('quarantine_count', 0) > 0:
            report.append(f"  📋 Will quarantine {plan['quarantine_count']} rows for review")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def get_actionable_steps(self, preview: DataPreview) -> List[Dict[str, Any]]:
        """
        Get list of actionable steps user can take.
        
        Args:
            preview: DataPreview object
            
        Returns:
            List of action dictionaries
        """
        actions = []
        
        if preview.status == PreviewStatus.READY_TO_IMPORT:
            actions.append({
                'type': 'import',
                'title': 'Import Data',
                'description': f'Import {preview.summary.get("processable_rows", 0)} rows of data',
                'button_text': 'Import Now',
                'button_color': 'green'
            })
        
        if preview.status == PreviewStatus.NEEDS_REVIEW:
            actions.append({
                'type': 'review',
                'title': 'Review Issues',
                'description': f'Review {len(preview.issues_by_severity.get("warning", []))} warnings before import',
                'button_text': 'Review & Import',
                'button_color': 'orange'
            })
        
        if preview.quarantined_sample is not None and not preview.quarantined_sample.empty:
            actions.append({
                'type': 'download_quarantine',
                'title': 'Download Quarantined Data',
                'description': f'Download {preview.summary.get("quarantined_rows", 0)} rows that need fixing',
                'button_text': 'Download CSV',
                'button_color': 'blue'
            })
        
        if preview.status == PreviewStatus.CANNOT_IMPORT:
            actions.append({
                'type': 'fix_file',
                'title': 'Fix File Issues',
                'description': 'File has critical issues that prevent import',
                'button_text': 'Download Template',
                'button_color': 'red'
            })
        
        return actions
    
    def _determine_status(self, validation_result: ValidationResult) -> PreviewStatus:
        """Determine the overall status of the preview"""
        if validation_result.has_critical_issues:
            if validation_result.processable_rows == 0:
                return PreviewStatus.CANNOT_IMPORT
            else:
                return PreviewStatus.NEEDS_REVIEW
        
        # Check for warnings
        warning_count = sum(1 for issue in validation_result.issues 
                          if issue.severity == ValidationSeverity.WARNING)
        
        if warning_count > 0:
            return PreviewStatus.NEEDS_REVIEW
        
        return PreviewStatus.READY_TO_IMPORT
    
    def _group_issues_by_severity(self, issues: List[ValidationIssue]) -> Dict[str, List[ValidationIssue]]:
        """Group validation issues by severity"""
        grouped = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        for issue in issues:
            grouped[issue.severity.value].append(issue)
        
        return grouped
    
    def _create_summary(
        self, 
        detection_result: FormatDetectionResult,
        validation_result: ValidationResult,
        filename: str
    ) -> Dict[str, Any]:
        """Create summary statistics"""
        total_rows = validation_result.summary.get('total_rows', 0)
        processable_rows = validation_result.processable_rows
        
        success_rate = processable_rows / total_rows if total_rows > 0 else 0
        
        return {
            'filename': filename,
            'file_type': detection_result.file_type.value,
            'detection_confidence': detection_result.confidence,
            'total_rows': total_rows,
            'processable_rows': processable_rows,
            'quarantined_rows': validation_result.quarantined_rows,
            'success_rate': success_rate,
            'column_mapping': validation_result.summary.get('column_mapping', {}),
            'timestamp': datetime.now().isoformat()
        }
    
    def _create_sample_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Create sample data for preview"""
        if df.empty:
            return df
        
        # Get sample rows
        sample = df.head(self.max_sample_rows).copy()
        
        # Add metadata column for context
        sample['_row_type'] = data_type
        
        return sample
    
    def _generate_recommendations(
        self, 
        detection_result: FormatDetectionResult,
        validation_result: ValidationResult
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Include detection recommendations
        recommendations.extend(detection_result.recommendations)
        
        # Add validation-specific recommendations
        if validation_result.quarantined_rows > 0:
            recommendations.append(
                f"Review and fix {validation_result.quarantined_rows} quarantined rows "
                "to improve data quality"
            )
        
        # Critical issues recommendations
        critical_issues = [issue for issue in validation_result.issues 
                          if issue.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(
                "Fix critical data issues before importing to prevent data loss"
            )
        
        # Date format recommendations
        date_issues = [issue for issue in validation_result.issues 
                      if 'date' in issue.column.lower()]
        if date_issues:
            recommendations.append(
                "Consider standardizing date formats for more reliable processing"
            )
        
        return recommendations
    
    def _create_import_plan(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Create detailed import plan"""
        plan = {
            'will_import': validation_result.processable_rows > 0,
            'import_count': validation_result.processable_rows,
            'quarantine_count': validation_result.quarantined_rows,
            'data_transformations': [],
            'estimated_time': self._estimate_import_time(validation_result.processable_rows)
        }
        
        # Document transformations that were applied
        transformations = set()
        for issue in validation_result.issues:
            if issue.corrected_value is not None:
                if 'normalized' in issue.message.lower():
                    transformations.add(f"Normalize {issue.column} values")
                elif 'rounded' in issue.message.lower():
                    transformations.add(f"Round {issue.column} to integers")
                elif 'parsed' in issue.message.lower():
                    transformations.add(f"Parse {issue.column} dates")
        
        plan['data_transformations'] = list(transformations)
        
        return plan
    
    def _estimate_import_time(self, row_count: int) -> str:
        """Estimate import time based on row count"""
        if row_count < 100:
            return "< 1 second"
        elif row_count < 1000:
            return "1-5 seconds"
        elif row_count < 10000:
            return "5-30 seconds"
        else:
            return "30+ seconds"
    
    def _generate_warnings(self, validation_result: ValidationResult) -> List[str]:
        """Generate important warnings for the user"""
        warnings = []
        
        # High quarantine rate warning
        if validation_result.summary.get('total_rows', 0) > 0:
            quarantine_rate = validation_result.quarantined_rows / validation_result.summary['total_rows']
            if quarantine_rate > 0.2:  # More than 20% quarantined
                warnings.append(
                    f"High quarantine rate ({quarantine_rate:.1%}) - consider reviewing source data quality"
                )
        
        # Future date warnings
        future_date_issues = [issue for issue in validation_result.issues 
                             if 'future' in issue.message.lower()]
        if future_date_issues:
            warnings.append(
                f"Found {len(future_date_issues)} records with future dates - verify data accuracy"
            )
        
        # Empty required field warnings
        empty_field_issues = [issue for issue in validation_result.issues 
                             if 'empty' in issue.message.lower() or 'null' in issue.message.lower()]
        if len(empty_field_issues) > 5:  # Many empty fields
            warnings.append(
                "Multiple records have empty required fields - check data completeness"
            )
        
        return warnings