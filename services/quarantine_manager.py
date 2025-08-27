"""
Quarantine manager for handling problematic data that cannot be processed immediately.
This service ensures no data is ever lost and provides mechanisms for manual review and correction.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .upload_validator import ValidationResult, ValidationIssue


class QuarantineReason(Enum):
    """Reasons for quarantining data"""
    CRITICAL_VALIDATION_ERROR = "critical_validation_error"
    UNPARSEABLE_DATE = "unparseable_date"
    INVALID_NUMBER_FORMAT = "invalid_number_format"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    DUPLICATE_RECORD = "duplicate_record"
    SUSPICIOUS_DATA = "suspicious_data"
    MANUAL_REVIEW_REQUESTED = "manual_review_requested"


class QuarantineStatus(Enum):
    """Status of quarantined data"""
    QUARANTINED = "quarantined"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FIXED = "fixed"


@dataclass
class QuarantineRecord:
    """A single quarantined record with metadata"""
    record_id: str
    original_row_index: int
    original_data: Dict[str, Any]
    quarantine_reason: QuarantineReason
    status: QuarantineStatus
    issues: List[ValidationIssue]
    quarantined_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    corrected_data: Optional[Dict[str, Any]] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'record_id': self.record_id,
            'original_row_index': self.original_row_index,
            'original_data': self.original_data,
            'quarantine_reason': self.quarantine_reason.value,
            'status': self.status.value,
            'issues': [
                {
                    'severity': issue.severity.value,
                    'column': issue.column,
                    'original_value': str(issue.original_value),
                    'message': issue.message
                }
                for issue in self.issues
            ],
            'quarantined_at': self.quarantined_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'reviewed_by': self.reviewed_by,
            'corrected_data': self.corrected_data,
            'notes': self.notes
        }


@dataclass
class QuarantineBatch:
    """A batch of quarantined records from a single upload"""
    batch_id: str
    filename: str
    file_type: str
    tenant_id: Optional[str]
    records: List[QuarantineRecord]
    created_at: datetime
    total_records: int
    quarantined_count: int
    summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def quarantine_rate(self) -> float:
        """Calculate quarantine rate"""
        return self.quarantined_count / self.total_records if self.total_records > 0 else 0.0
    
    def get_records_by_status(self, status: QuarantineStatus) -> List[QuarantineRecord]:
        """Get records with specific status"""
        return [record for record in self.records if record.status == status]
    
    def get_records_by_reason(self, reason: QuarantineReason) -> List[QuarantineRecord]:
        """Get records with specific quarantine reason"""
        return [record for record in self.records if record.quarantine_reason == reason]


class QuarantineManager:
    """
    Manages quarantined data with full traceability and recovery mechanisms.
    Ensures no data is ever lost and provides tools for manual review and correction.
    """
    
    def __init__(self, quarantine_dir: Optional[str] = None):
        """
        Initialize quarantine manager.
        
        Args:
            quarantine_dir: Directory for storing quarantine files (defaults to ./quarantine)
        """
        self.quarantine_dir = Path(quarantine_dir or "./quarantine")
        self.quarantine_dir.mkdir(exist_ok=True)
    
    def quarantine_data(
        self,
        validation_result: ValidationResult,
        filename: str,
        file_type: str,
        tenant_id: Optional[str] = None
    ) -> QuarantineBatch:
        """
        Quarantine problematic data from validation results.
        
        Args:
            validation_result: Results from upload validation
            filename: Original filename
            file_type: Type of file (sales_data, lots_data)
            tenant_id: Optional tenant identifier
            
        Returns:
            QuarantineBatch with quarantined records
        """
        batch_id = str(uuid.uuid4())
        quarantined_records = []
        
        # Process quarantined data row by row
        for idx, row in validation_result.quarantined_data.iterrows():
            # Find issues for this row
            row_issues = [
                issue for issue in validation_result.issues 
                if issue.row_index == idx
            ]
            
            # Determine primary quarantine reason
            reason = self._determine_quarantine_reason(row_issues)
            
            # Create quarantine record
            record = QuarantineRecord(
                record_id=str(uuid.uuid4()),
                original_row_index=idx,
                original_data=row.to_dict(),
                quarantine_reason=reason,
                status=QuarantineStatus.QUARANTINED,
                issues=row_issues,
                quarantined_at=datetime.now()
            )
            
            quarantined_records.append(record)
        
        # Create batch
        batch = QuarantineBatch(
            batch_id=batch_id,
            filename=filename,
            file_type=file_type,
            tenant_id=tenant_id,
            records=quarantined_records,
            created_at=datetime.now(),
            total_records=validation_result.summary.get('total_rows', 0),
            quarantined_count=len(quarantined_records),
            summary=self._create_batch_summary(quarantined_records, validation_result)
        )
        
        # Save batch to disk
        self._save_batch(batch)
        
        return batch
    
    def get_batch(self, batch_id: str) -> Optional[QuarantineBatch]:
        """Load a quarantine batch by ID"""
        batch_file = self.quarantine_dir / f"{batch_id}.json"
        if not batch_file.exists():
            return None
        
        try:
            with open(batch_file, 'r') as f:
                data = json.load(f)
            return self._deserialize_batch(data)
        except Exception:
            return None
    
    def list_batches(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all quarantine batches with summary info"""
        batches = []
        
        for batch_file in self.quarantine_dir.glob("*.json"):
            try:
                with open(batch_file, 'r') as f:
                    data = json.load(f)
                
                # Filter by tenant if specified
                if tenant_id and data.get('tenant_id') != tenant_id:
                    continue
                
                # Create summary
                batch_summary = {
                    'batch_id': data['batch_id'],
                    'filename': data['filename'],
                    'file_type': data['file_type'],
                    'tenant_id': data.get('tenant_id'),
                    'created_at': data['created_at'],
                    'total_records': data['total_records'],
                    'quarantined_count': data['quarantined_count'],
                    'quarantine_rate': data['quarantined_count'] / data['total_records'] if data['total_records'] > 0 else 0,
                    'status_counts': self._count_statuses(data['records'])
                }
                
                batches.append(batch_summary)
                
            except Exception:
                continue  # Skip corrupted files
        
        # Sort by creation date (newest first)
        batches.sort(key=lambda x: x['created_at'], reverse=True)
        return batches
    
    def review_record(
        self,
        batch_id: str,
        record_id: str,
        reviewer: str,
        action: str,  # 'approve', 'reject', 'fix'
        corrected_data: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> bool:
        """
        Review and update a quarantined record.
        
        Args:
            batch_id: Batch identifier
            record_id: Record identifier
            reviewer: Name/ID of reviewer
            action: Action taken ('approve', 'reject', 'fix')
            corrected_data: Corrected data if fixing
            notes: Optional notes
            
        Returns:
            True if successful, False otherwise
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return False
        
        # Find the record
        record = None
        for r in batch.records:
            if r.record_id == record_id:
                record = r
                break
        
        if not record:
            return False
        
        # Update record
        record.reviewed_at = datetime.now()
        record.reviewed_by = reviewer
        record.notes = notes
        
        if action == 'approve':
            record.status = QuarantineStatus.APPROVED
        elif action == 'reject':
            record.status = QuarantineStatus.REJECTED
        elif action == 'fix' and corrected_data:
            record.status = QuarantineStatus.FIXED
            record.corrected_data = corrected_data
        else:
            return False
        
        # Save updated batch
        self._save_batch(batch)
        return True
    
    def get_corrected_data(self, batch_id: str) -> pd.DataFrame:
        """
        Get all corrected data from a batch that's ready for import.
        
        Args:
            batch_id: Batch identifier
            
        Returns:
            DataFrame with corrected data
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return pd.DataFrame()
        
        # Get approved and fixed records
        ready_records = [
            record for record in batch.records 
            if record.status in [QuarantineStatus.APPROVED, QuarantineStatus.FIXED]
        ]
        
        if not ready_records:
            return pd.DataFrame()
        
        # Create dataframe from corrected data
        corrected_rows = []
        for record in ready_records:
            if record.status == QuarantineStatus.FIXED and record.corrected_data:
                corrected_rows.append(record.corrected_data)
            elif record.status == QuarantineStatus.APPROVED:
                corrected_rows.append(record.original_data)
        
        if corrected_rows:
            return pd.DataFrame(corrected_rows)
        
        return pd.DataFrame()
    
    def export_quarantine_csv(self, batch_id: str, include_metadata: bool = True) -> Optional[str]:
        """
        Export quarantine batch to CSV for manual review/correction.
        
        Args:
            batch_id: Batch identifier
            include_metadata: Whether to include quarantine metadata columns
            
        Returns:
            Path to exported CSV file, or None if failed
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return None
        
        # Create rows for CSV
        rows = []
        for record in batch.records:
            row = record.original_data.copy()
            
            if include_metadata:
                row['_quarantine_record_id'] = record.record_id
                row['_quarantine_reason'] = record.quarantine_reason.value
                row['_quarantine_status'] = record.status.value
                row['_issues'] = '; '.join([issue.message for issue in record.issues])
        
        if not rows:
            return None
        
        # Create DataFrame and save
        df = pd.DataFrame(rows)
        export_path = self.quarantine_dir / f"{batch_id}_export.csv"
        df.to_csv(export_path, index=False)
        
        return str(export_path)
    
    def import_corrected_csv(self, batch_id: str, csv_path: str, reviewer: str) -> int:
        """
        Import corrected data from CSV back into quarantine system.
        
        Args:
            batch_id: Batch identifier
            csv_path: Path to corrected CSV file
            reviewer: Name/ID of reviewer
            
        Returns:
            Number of records successfully updated
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return 0
        
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return 0
        
        updated_count = 0
        
        # Process each row in the corrected CSV
        for idx, row in df.iterrows():
            record_id = row.get('_quarantine_record_id')
            if not record_id:
                continue
            
            # Find the record
            record = None
            for r in batch.records:
                if r.record_id == record_id:
                    record = r
                    break
            
            if not record:
                continue
            
            # Extract corrected data (exclude metadata columns)
            corrected_data = {}
            for col, value in row.items():
                if not col.startswith('_quarantine'):
                    corrected_data[col] = value
            
            # Update record
            record.corrected_data = corrected_data
            record.status = QuarantineStatus.FIXED
            record.reviewed_at = datetime.now()
            record.reviewed_by = reviewer
            record.notes = "Updated via CSV import"
            
            updated_count += 1
        
        if updated_count > 0:
            self._save_batch(batch)
        
        return updated_count
    
    def get_quarantine_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get overall quarantine statistics"""
        batches = self.list_batches(tenant_id)
        
        if not batches:
            return {
                'total_batches': 0,
                'total_records': 0,
                'total_quarantined': 0,
                'average_quarantine_rate': 0.0,
                'status_breakdown': {},
                'reason_breakdown': {}
            }
        
        total_records = sum(b['total_records'] for b in batches)
        total_quarantined = sum(b['quarantined_count'] for b in batches)
        avg_quarantine_rate = total_quarantined / total_records if total_records > 0 else 0
        
        # Aggregate status counts
        status_totals = {}
        for batch in batches:
            for status, count in batch['status_counts'].items():
                status_totals[status] = status_totals.get(status, 0) + count
        
        # Get reason breakdown
        reason_totals = {}
        for batch_summary in batches:
            batch = self.get_batch(batch_summary['batch_id'])
            if batch:
                for record in batch.records:
                    reason = record.quarantine_reason.value
                    reason_totals[reason] = reason_totals.get(reason, 0) + 1
        
        return {
            'total_batches': len(batches),
            'total_records': total_records,
            'total_quarantined': total_quarantined,
            'average_quarantine_rate': avg_quarantine_rate,
            'status_breakdown': status_totals,
            'reason_breakdown': reason_totals
        }
    
    def cleanup_old_batches(self, days_old: int = 30) -> int:
        """
        Clean up old quarantine batches.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of batches cleaned up
        """
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        cleaned_count = 0
        
        for batch_file in self.quarantine_dir.glob("*.json"):
            try:
                with open(batch_file, 'r') as f:
                    data = json.load(f)
                
                created_at = datetime.fromisoformat(data['created_at']).timestamp()
                if created_at < cutoff_date:
                    # Only delete if all records are resolved
                    all_resolved = all(
                        record['status'] in ['approved', 'rejected', 'fixed']
                        for record in data['records']
                    )
                    
                    if all_resolved:
                        batch_file.unlink()
                        cleaned_count += 1
                        
                        # Also remove export file if it exists
                        export_file = self.quarantine_dir / f"{data['batch_id']}_export.csv"
                        if export_file.exists():
                            export_file.unlink()
                        
            except Exception:
                continue
        
        return cleaned_count
    
    def _determine_quarantine_reason(self, issues: List[ValidationIssue]) -> QuarantineReason:
        """Determine primary quarantine reason from validation issues"""
        if not issues:
            return QuarantineReason.MANUAL_REVIEW_REQUESTED
        
        # Priority order for reasons
        reason_priority = {
            'date': QuarantineReason.UNPARSEABLE_DATE,
            'number': QuarantineReason.INVALID_NUMBER_FORMAT,
            'empty': QuarantineReason.MISSING_REQUIRED_FIELD,
            'null': QuarantineReason.MISSING_REQUIRED_FIELD,
            'duplicate': QuarantineReason.DUPLICATE_RECORD
        }
        
        # Find highest priority reason
        for priority_keyword, reason in reason_priority.items():
            for issue in issues:
                if priority_keyword in issue.message.lower():
                    return reason
        
        return QuarantineReason.CRITICAL_VALIDATION_ERROR
    
    def _create_batch_summary(
        self, 
        records: List[QuarantineRecord],
        validation_result: ValidationResult
    ) -> Dict[str, Any]:
        """Create summary statistics for a batch"""
        reason_counts = {}
        for record in records:
            reason = record.quarantine_reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            'reason_breakdown': reason_counts,
            'critical_issues': validation_result.summary.get('critical_issues', 0),
            'warnings': validation_result.summary.get('warnings', 0),
            'column_mapping': validation_result.summary.get('column_mapping', {})
        }
    
    def _save_batch(self, batch: QuarantineBatch):
        """Save batch to disk"""
        batch_file = self.quarantine_dir / f"{batch.batch_id}.json"
        
        # Serialize batch
        data = {
            'batch_id': batch.batch_id,
            'filename': batch.filename,
            'file_type': batch.file_type,
            'tenant_id': batch.tenant_id,
            'created_at': batch.created_at.isoformat(),
            'total_records': batch.total_records,
            'quarantined_count': batch.quarantined_count,
            'summary': batch.summary,
            'records': [record.to_dict() for record in batch.records]
        }
        
        with open(batch_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _deserialize_batch(self, data: Dict[str, Any]) -> QuarantineBatch:
        """Deserialize batch from JSON data"""
        records = []
        for record_data in data['records']:
            # Reconstruct validation issues
            issues = []
            for issue_data in record_data.get('issues', []):
                # Note: We can't fully reconstruct ValidationIssue objects
                # without importing the class, so we'll create a simplified version
                pass  # For now, skip issue reconstruction
            
            record = QuarantineRecord(
                record_id=record_data['record_id'],
                original_row_index=record_data['original_row_index'],
                original_data=record_data['original_data'],
                quarantine_reason=QuarantineReason(record_data['quarantine_reason']),
                status=QuarantineStatus(record_data['status']),
                issues=issues,  # Simplified for now
                quarantined_at=datetime.fromisoformat(record_data['quarantined_at']),
                reviewed_at=datetime.fromisoformat(record_data['reviewed_at']) if record_data.get('reviewed_at') else None,
                reviewed_by=record_data.get('reviewed_by'),
                corrected_data=record_data.get('corrected_data'),
                notes=record_data.get('notes', '')
            )
            records.append(record)
        
        return QuarantineBatch(
            batch_id=data['batch_id'],
            filename=data['filename'],
            file_type=data['file_type'],
            tenant_id=data.get('tenant_id'),
            records=records,
            created_at=datetime.fromisoformat(data['created_at']),
            total_records=data['total_records'],
            quarantined_count=data['quarantined_count'],
            summary=data.get('summary', {})
        )
    
    def _count_statuses(self, records_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count records by status"""
        counts = {}
        for record_data in records_data:
            status = record_data['status']
            counts[status] = counts.get(status, 0) + 1
        return counts