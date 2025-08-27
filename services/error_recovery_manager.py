#!/usr/bin/env python3
"""
ERROR RECOVERY MANAGER
Central error management system for FIFO COGS processing.
Ensures that one bad SKU never stops processing of hundreds of good ones.
"""

import logging
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import os

class ErrorSeverity(Enum):
    """Error severity levels"""
    CRITICAL = "critical"      # System cannot continue
    HIGH = "high"             # SKU processing blocked
    MEDIUM = "medium"         # Data quality issue
    LOW = "low"              # Warning only

class ErrorCategory(Enum):
    """Categories of errors for better organization"""
    NEGATIVE_INVENTORY = "negative_inventory"
    MISSING_LOTS = "missing_lots"
    DATA_CONFLICT = "data_conflict"
    DATE_MISMATCH = "date_mismatch"
    COST_ANOMALY = "cost_anomaly"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"

@dataclass
class FIFOError:
    """Represents a single error encountered during FIFO processing"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    sku: str
    message: str
    suggested_fix: str
    data_context: Dict[str, Any]
    timestamp: datetime
    processed: bool = False
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['category'] = self.category.value
        result['severity'] = self.severity.value
        result['timestamp'] = self.timestamp.isoformat()
        return result

class ErrorRecoveryManager:
    """
    Central error management system for FIFO processing.
    Handles errors gracefully without stopping entire batch processing.
    """
    
    def __init__(self, output_dir: str = "error_recovery"):
        self.output_dir = output_dir
        self.errors: List[FIFOError] = []
        self.error_counter = 0
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize error tracking files
        self.error_log_file = os.path.join(self.output_dir, f"error_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        self.quarantine_file = os.path.join(self.output_dir, f"quarantine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
    def record_error(self, 
                    category: ErrorCategory,
                    severity: ErrorSeverity,
                    sku: str,
                    message: str,
                    suggested_fix: str,
                    data_context: Dict[str, Any] = None) -> str:
        """
        Record an error for later handling.
        Returns error_id for tracking.
        """
        self.error_counter += 1
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.error_counter:04d}"
        
        error = FIFOError(
            error_id=error_id,
            category=category,
            severity=severity,
            sku=sku,
            message=message,
            suggested_fix=suggested_fix,
            data_context=data_context or {},
            timestamp=datetime.now()
        )
        
        self.errors.append(error)
        
        # Log based on severity
        log_message = f"[{error_id}] {sku}: {message}"
        if severity == ErrorSeverity.CRITICAL:
            self.logger.error(log_message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
        return error_id
    
    def handle_negative_inventory(self, 
                                sku: str, 
                                requested_qty: int, 
                                available_qty: int,
                                lot_details: List[Dict]) -> str:
        """Handle negative inventory scenario with specific recommendations"""
        
        shortage = requested_qty - available_qty
        
        suggested_fixes = []
        
        # Analyze lot details to provide specific recommendations
        if not lot_details:
            suggested_fixes.append(f"Upload missing purchase lots for SKU {sku}")
        else:
            latest_lot_date = max(lot['received_date'] for lot in lot_details)
            suggested_fixes.append(f"Check if recent lots after {latest_lot_date} are missing")
        
        if available_qty > 0:
            suggested_fixes.append(f"Partial processing: {available_qty} units available, {shortage} short")
        
        suggested_fixes.append(f"Verify sales data for {sku} - check for duplicates or errors")
        
        return self.record_error(
            category=ErrorCategory.NEGATIVE_INVENTORY,
            severity=ErrorSeverity.HIGH,
            sku=sku,
            message=f"Insufficient inventory: need {requested_qty}, have {available_qty} (short by {shortage})",
            suggested_fix=" | ".join(suggested_fixes),
            data_context={
                'requested_qty': requested_qty,
                'available_qty': available_qty,
                'shortage': shortage,
                'lot_count': len(lot_details),
                'lot_details': lot_details
            }
        )
    
    def handle_missing_lots(self, sku: str, sales_qty: int, sale_date: str) -> str:
        """Handle missing lots scenario"""
        
        suggested_fixes = [
            f"Upload purchase lots for SKU {sku}",
            f"Check if {sku} is a valid/active SKU",
            f"Verify SKU spelling and format",
            f"Review sales data for potential SKU mapping errors"
        ]
        
        return self.record_error(
            category=ErrorCategory.MISSING_LOTS,
            severity=ErrorSeverity.HIGH,
            sku=sku,
            message=f"No purchase lots found for SKU {sku} (sales: {sales_qty} units on {sale_date})",
            suggested_fix=" | ".join(suggested_fixes),
            data_context={
                'sales_qty': sales_qty,
                'sale_date': sale_date
            }
        )
    
    def handle_date_mismatch(self, 
                           sku: str, 
                           sale_date: str, 
                           earliest_lot_date: str) -> str:
        """Handle sales before inventory received"""
        
        suggested_fixes = [
            f"Verify sale date {sale_date} for SKU {sku}",
            f"Check if older lots exist before {earliest_lot_date}",
            "Sales date may be incorrect or lot data incomplete",
            "Consider adjusting sale date or uploading missing historical lots"
        ]
        
        return self.record_error(
            category=ErrorCategory.DATE_MISMATCH,
            severity=ErrorSeverity.MEDIUM,
            sku=sku,
            message=f"Sale date {sale_date} before earliest lot date {earliest_lot_date}",
            suggested_fix=" | ".join(suggested_fixes),
            data_context={
                'sale_date': sale_date,
                'earliest_lot_date': earliest_lot_date
            }
        )
    
    def handle_cost_anomaly(self, 
                          sku: str, 
                          current_cost: float, 
                          average_cost: float,
                          variance_percent: float) -> str:
        """Handle significant cost variations"""
        
        if variance_percent > 0:
            direction = "increase"
        else:
            direction = "decrease"
            
        suggested_fixes = [
            f"Verify cost data for SKU {sku} - {abs(variance_percent):.1f}% {direction}",
            "Check for data entry errors in unit price or freight cost",
            "Confirm if cost change is legitimate (supplier change, etc.)",
            "Review PO details for accuracy"
        ]
        
        return self.record_error(
            category=ErrorCategory.COST_ANOMALY,
            severity=ErrorSeverity.LOW,
            sku=sku,
            message=f"Cost anomaly: current ${current_cost:.2f} vs average ${average_cost:.2f} ({variance_percent:+.1f}%)",
            suggested_fix=" | ".join(suggested_fixes),
            data_context={
                'current_cost': current_cost,
                'average_cost': average_cost,
                'variance_percent': variance_percent
            }
        )
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[FIFOError]:
        """Get all errors of a specific category"""
        return [error for error in self.errors if error.category == category]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[FIFOError]:
        """Get all errors of a specific severity"""
        return [error for error in self.errors if error.severity == severity]
    
    def get_errors_by_sku(self, sku: str) -> List[FIFOError]:
        """Get all errors for a specific SKU"""
        return [error for error in self.errors if error.sku == sku]
    
    def get_blocking_errors(self) -> List[FIFOError]:
        """Get errors that prevent processing (CRITICAL or HIGH severity)"""
        return [error for error in self.errors 
                if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]]
    
    def get_skus_with_errors(self) -> List[str]:
        """Get list of SKUs that have errors"""
        return list(set(error.sku for error in self.errors))
    
    def get_processable_skus(self, all_skus: List[str]) -> List[str]:
        """Get SKUs that can still be processed (no blocking errors)"""
        blocked_skus = set(error.sku for error in self.get_blocking_errors())
        return [sku for sku in all_skus if sku not in blocked_skus]
    
    def mark_error_resolved(self, error_id: str, resolution: str):
        """Mark an error as resolved with resolution notes"""
        for error in self.errors:
            if error.error_id == error_id:
                error.processed = True
                error.resolution = resolution
                break
    
    def export_error_report(self) -> Dict[str, str]:
        """Export comprehensive error report"""
        
        # JSON error log
        error_data = [error.to_dict() for error in self.errors]
        
        with open(self.error_log_file, 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'total_errors': len(self.errors),
                'error_summary': self._get_error_summary(),
                'errors': error_data
            }, f, indent=2)
        
        # CSV quarantine report
        if self.errors:
            with open(self.quarantine_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Error_ID', 'Category', 'Severity', 'SKU', 'Message', 
                    'Suggested_Fix', 'Timestamp', 'Data_Context'
                ])
                
                for error in self.errors:
                    writer.writerow([
                        error.error_id,
                        error.category.value,
                        error.severity.value,
                        error.sku,
                        error.message,
                        error.suggested_fix,
                        error.timestamp.isoformat(),
                        json.dumps(error.data_context)
                    ])
        
        return {
            'error_log': self.error_log_file,
            'quarantine_report': self.quarantine_file,
            'summary': self._generate_summary_report()
        }
    
    def _get_error_summary(self) -> Dict[str, Any]:
        """Generate error summary statistics"""
        total = len(self.errors)
        if total == 0:
            return {"total_errors": 0}
        
        by_category = {}
        by_severity = {}
        by_sku = {}
        
        for error in self.errors:
            # By category
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # By severity
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # By SKU
            sku = error.sku
            by_sku[sku] = by_sku.get(sku, 0) + 1
        
        return {
            'total_errors': total,
            'by_category': by_category,
            'by_severity': by_severity,
            'affected_skus': len(by_sku),
            'top_problem_skus': sorted(by_sku.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _generate_summary_report(self) -> str:
        """Generate human-readable summary report"""
        if not self.errors:
            return "✅ No errors encountered during processing"
        
        summary = self._get_error_summary()
        
        report_lines = [
            "🔍 FIFO PROCESSING ERROR SUMMARY",
            "=" * 50,
            f"Total Errors: {summary['total_errors']}",
            f"Affected SKUs: {summary['affected_skus']}",
            "",
            "By Severity:",
            f"  🔴 Critical: {summary['by_severity'].get('critical', 0)}",
            f"  🟡 High: {summary['by_severity'].get('high', 0)}",
            f"  🟠 Medium: {summary['by_severity'].get('medium', 0)}",
            f"  ⚪ Low: {summary['by_severity'].get('low', 0)}",
            "",
            "By Category:",
        ]
        
        for category, count in summary['by_category'].items():
            report_lines.append(f"  • {category.replace('_', ' ').title()}: {count}")
        
        if summary['top_problem_skus']:
            report_lines.extend([
                "",
                "Top Problem SKUs:",
            ])
            for sku, count in summary['top_problem_skus'][:5]:
                report_lines.append(f"  • {sku}: {count} errors")
        
        blocking_errors = len(self.get_blocking_errors())
        processable_errors = len(self.errors) - blocking_errors
        
        report_lines.extend([
            "",
            f"🚫 Blocking Errors: {blocking_errors} (prevent SKU processing)",
            f"⚠️  Non-blocking Errors: {processable_errors} (warnings only)",
            "",
            "📁 Detailed Reports:",
            f"  • JSON Log: {self.error_log_file}",
            f"  • CSV Report: {self.quarantine_file}",
        ])
        
        return "\n".join(report_lines)
    
    def can_continue_processing(self) -> Tuple[bool, List[str]]:
        """
        Determine if processing can continue and which SKUs can be processed.
        Returns (can_continue, processable_skus)
        """
        critical_errors = self.get_errors_by_severity(ErrorSeverity.CRITICAL)
        
        if critical_errors:
            return False, []
        
        # Get SKUs that don't have blocking errors
        all_skus = list(set(error.sku for error in self.errors))
        processable_skus = self.get_processable_skus(all_skus)
        
        return True, processable_skus
    
    def get_actionable_steps(self) -> List[str]:
        """Get prioritized list of actionable steps to resolve errors"""
        steps = []
        
        # Critical errors first
        critical_errors = self.get_errors_by_severity(ErrorSeverity.CRITICAL)
        if critical_errors:
            steps.append("🔴 CRITICAL: Fix these issues before any processing:")
            for error in critical_errors:
                steps.append(f"  • {error.sku}: {error.suggested_fix}")
            steps.append("")
        
        # High severity errors
        high_errors = self.get_errors_by_severity(ErrorSeverity.HIGH)
        if high_errors:
            steps.append("🟡 HIGH PRIORITY: Fix to process affected SKUs:")
            for error in high_errors:
                steps.append(f"  • {error.sku}: {error.suggested_fix}")
            steps.append("")
        
        # Missing lots
        missing_lots = self.get_errors_by_category(ErrorCategory.MISSING_LOTS)
        if missing_lots:
            skus = [error.sku for error in missing_lots]
            steps.append(f"📦 Upload missing purchase lots for: {', '.join(skus)}")
        
        # Negative inventory
        negative_inv = self.get_errors_by_category(ErrorCategory.NEGATIVE_INVENTORY)
        if negative_inv:
            skus = [error.sku for error in negative_inv]
            steps.append(f"📉 Check inventory/sales data for: {', '.join(skus)}")
        
        if not steps:
            steps.append("✅ No critical issues found")
        
        return steps

# Usage example functions
def demo_error_scenarios():
    """Demonstrate various error scenarios"""
    
    manager = ErrorRecoveryManager("demo_errors")
    
    # Negative inventory scenario
    manager.handle_negative_inventory(
        sku="ABC123",
        requested_qty=1000,
        available_qty=750,
        lot_details=[
            {'lot_id': 'LOT001', 'received_date': '2025-01-01', 'remaining': 500},
            {'lot_id': 'LOT002', 'received_date': '2025-01-15', 'remaining': 250}
        ]
    )
    
    # Missing lots scenario
    manager.handle_missing_lots(
        sku="XYZ789",
        sales_qty=500,
        sale_date="2025-01-20"
    )
    
    # Date mismatch scenario
    manager.handle_date_mismatch(
        sku="DEF456",
        sale_date="2024-12-15",
        earliest_lot_date="2025-01-01"
    )
    
    # Cost anomaly scenario
    manager.handle_cost_anomaly(
        sku="GHI789",
        current_cost=15.50,
        average_cost=10.25,
        variance_percent=51.2
    )
    
    # Export reports
    reports = manager.export_error_report()
    print(manager._generate_summary_report())
    print(f"\nReports generated:")
    for report_type, file_path in reports.items():
        print(f"  {report_type}: {file_path}")
    
    # Show actionable steps
    print("\nActionable Steps:")
    steps = manager.get_actionable_steps()
    for step in steps:
        print(step)

if __name__ == "__main__":
    demo_error_scenarios()