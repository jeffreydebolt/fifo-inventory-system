"""
Complete intelligent upload pipeline that integrates all components
for seamless handling of messy real-world data.
"""

from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from pathlib import Path
import logging

from .format_detector import FormatDetector, FormatDetectionResult
from .upload_validator import UploadValidator, ValidationResult
from .data_preview import DataPreviewService, DataPreview
from .quarantine_manager import QuarantineManager, QuarantineBatch


class IntelligentUploadPipeline:
    """
    Complete pipeline for intelligently processing uploaded CSV files.
    Handles real-world messy data gracefully while never losing information.
    """
    
    def __init__(self, quarantine_dir: Optional[str] = None):
        """
        Initialize the upload pipeline.
        
        Args:
            quarantine_dir: Directory for quarantine storage (optional)
        """
        self.detector = FormatDetector()
        self.validator = UploadValidator()
        self.preview_service = DataPreviewService()
        self.quarantine_manager = QuarantineManager(quarantine_dir)
        self.logger = logging.getLogger(__name__)
    
    def process_upload(
        self,
        file_path: str,
        tenant_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uploaded file through the complete pipeline.
        
        Args:
            file_path: Path to uploaded CSV file
            tenant_id: Optional tenant identifier
            filename: Optional original filename
            
        Returns:
            Complete processing results with recommendations
        """
        try:
            # Load file
            df = pd.read_csv(file_path)
            original_filename = filename or Path(file_path).name
            
            self.logger.info(f"Processing upload: {original_filename} ({len(df)} rows)")
            
            # Step 1: Format Detection
            detection_result = self.detector.detect_format(df)
            self.logger.info(f"Detected format: {detection_result.file_type.value} "
                           f"(confidence: {detection_result.confidence:.1%})")
            
            # Step 2: Data Validation
            if detection_result.file_type.value == "sales_data":
                validation_result = self.validator.validate_sales_data(df)
            elif detection_result.file_type.value == "lots_data":
                validation_result = self.validator.validate_lots_data(df)
            else:
                # Unknown format - try sales data as default
                validation_result = self.validator.validate_sales_data(df)
            
            # Step 3: Create Preview
            preview = self.preview_service.create_preview(
                detection_result,
                validation_result,
                original_filename
            )
            
            # Step 4: Quarantine if needed
            quarantine_batch = None
            if validation_result.quarantined_rows > 0:
                quarantine_batch = self.quarantine_manager.quarantine_data(
                    validation_result,
                    original_filename,
                    detection_result.file_type.value,
                    tenant_id
                )
            
            # Generate comprehensive results
            results = {
                'status': 'success',
                'filename': original_filename,
                'file_type': detection_result.file_type.value,
                'detection_confidence': detection_result.confidence,
                'processing_summary': {
                    'total_rows': validation_result.summary.get('total_rows', 0),
                    'processable_rows': validation_result.processable_rows,
                    'quarantined_rows': validation_result.quarantined_rows,
                    'success_rate': validation_result.processable_rows / validation_result.summary.get('total_rows', 1)
                },
                'preview': {
                    'status': preview.status.value,
                    'safe_to_import': preview.is_safe_to_import,
                    'requires_review': preview.requires_manual_review,
                    'actionable_steps': self.preview_service.get_actionable_steps(preview)
                },
                'issues': {
                    'critical_count': len(preview.issues_by_severity.get('critical', [])),
                    'warning_count': len(preview.issues_by_severity.get('warning', [])),
                    'info_count': len(preview.issues_by_severity.get('info', [])),
                    'sample_issues': [
                        f"Row {issue.row_index}: {issue.message}"
                        for issue in validation_result.issues[:5]
                    ]
                },
                'quarantine': {
                    'batch_id': quarantine_batch.batch_id if quarantine_batch else None,
                    'quarantine_rate': quarantine_batch.quarantine_rate if quarantine_batch else 0.0,
                    'export_path': None
                },
                'recommendations': preview.recommendations,
                'preview_report': self.preview_service.generate_preview_report(preview),
                'normalized_data': validation_result.normalized_data.to_dict('records') if not validation_result.normalized_data.empty else [],
                'column_mapping': validation_result.summary.get('column_mapping', {})
            }
            
            # Export quarantine data if available
            if quarantine_batch:
                export_path = self.quarantine_manager.export_quarantine_csv(
                    quarantine_batch.batch_id, 
                    include_metadata=True
                )
                results['quarantine']['export_path'] = export_path
            
            self.logger.info(f"Processing completed: {validation_result.processable_rows} processable, "
                           f"{validation_result.quarantined_rows} quarantined")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline error processing {file_path}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'filename': filename or Path(file_path).name,
                'recommendations': [
                    'Check file format and structure',
                    'Ensure file is a valid CSV',
                    'Contact support if the issue persists'
                ]
            }
    
    def get_import_ready_data(self, batch_id: str) -> pd.DataFrame:
        """
        Get data that's ready for import after review/correction.
        
        Args:
            batch_id: Quarantine batch identifier
            
        Returns:
            DataFrame with corrected data ready for import
        """
        return self.quarantine_manager.get_corrected_data(batch_id)
    
    def review_quarantined_record(
        self,
        batch_id: str,
        record_id: str,
        reviewer: str,
        action: str,
        corrected_data: Optional[Dict[str, Any]] = None,
        notes: str = ""
    ) -> bool:
        """
        Review a quarantined record.
        
        Args:
            batch_id: Quarantine batch identifier
            record_id: Record identifier
            reviewer: Reviewer name/ID
            action: Action to take ('approve', 'reject', 'fix')
            corrected_data: Corrected data if fixing
            notes: Optional notes
            
        Returns:
            True if successful
        """
        return self.quarantine_manager.review_record(
            batch_id, record_id, reviewer, action, corrected_data, notes
        )
    
    def import_corrected_csv(
        self,
        batch_id: str,
        csv_path: str,
        reviewer: str
    ) -> int:
        """
        Import corrected data from CSV.
        
        Args:
            batch_id: Quarantine batch identifier
            csv_path: Path to corrected CSV
            reviewer: Reviewer name/ID
            
        Returns:
            Number of records updated
        """
        return self.quarantine_manager.import_corrected_csv(
            batch_id, csv_path, reviewer
        )
    
    def get_quarantine_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get quarantine statistics"""
        return self.quarantine_manager.get_quarantine_statistics(tenant_id)
    
    def list_quarantine_batches(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List quarantine batches"""
        return self.quarantine_manager.list_batches(tenant_id)


class UploadAPIIntegration:
    """
    Integration helper for connecting the pipeline with existing upload APIs.
    Shows how to integrate with the current FIFO system safely.
    """
    
    def __init__(self, pipeline: IntelligentUploadPipeline):
        self.pipeline = pipeline
        
    def enhanced_upload_handler(
        self,
        uploaded_file,  # FastAPI UploadFile or similar
        tenant_id: str,
        file_type: str  # 'sales' or 'lots'
    ) -> Dict[str, Any]:
        """
        Enhanced upload handler that uses intelligent pipeline.
        
        This can replace or enhance existing upload endpoints.
        """
        try:
            # Save uploaded file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as temp_file:
                content = uploaded_file.file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Process through pipeline
            results = self.pipeline.process_upload(
                temp_file_path,
                tenant_id=tenant_id,
                filename=uploaded_file.filename
            )
            
            # Clean up temp file
            Path(temp_file_path).unlink()
            
            # Determine response based on results
            if results['status'] == 'success':
                if results['preview']['safe_to_import']:
                    return {
                        'status': 'ready_for_import',
                        'message': 'Data is ready to import immediately',
                        'data': results['normalized_data'],
                        'summary': results['processing_summary'],
                        'recommendations': results['recommendations']
                    }
                elif results['preview']['requires_review']:
                    return {
                        'status': 'needs_review',
                        'message': 'Data needs review before import',
                        'quarantine_batch_id': results['quarantine']['batch_id'],
                        'quarantine_export_path': results['quarantine']['export_path'],
                        'summary': results['processing_summary'],
                        'issues': results['issues'],
                        'actionable_steps': results['preview']['actionable_steps'],
                        'recommendations': results['recommendations']
                    }
                else:
                    return {
                        'status': 'cannot_import',
                        'message': 'Data has critical issues that prevent import',
                        'quarantine_batch_id': results['quarantine']['batch_id'],
                        'quarantine_export_path': results['quarantine']['export_path'],
                        'issues': results['issues'],
                        'recommendations': results['recommendations']
                    }
            else:
                return {
                    'status': 'error',
                    'message': f"Processing failed: {results.get('error', 'Unknown error')}",
                    'recommendations': results.get('recommendations', [])
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Upload processing failed: {str(e)}",
                'recommendations': [
                    'Check file format and structure',
                    'Ensure file is a valid CSV',
                    'Contact support if the issue persists'
                ]
            }
    
    def create_preview_endpoint_handler(self) -> callable:
        """Create a preview endpoint that shows what will be imported"""
        def preview_handler(file_path: str, tenant_id: str = None):
            results = self.pipeline.process_upload(file_path, tenant_id)
            return {
                'preview_report': results.get('preview_report', ''),
                'processing_summary': results.get('processing_summary', {}),
                'actionable_steps': results.get('preview', {}).get('actionable_steps', []),
                'recommendations': results.get('recommendations', [])
            }
        return preview_handler
    
    def create_quarantine_review_endpoint_handler(self) -> callable:
        """Create endpoint for reviewing quarantined data"""
        def review_handler(
            batch_id: str, 
            record_id: str, 
            action: str, 
            reviewer: str,
            corrected_data: Dict[str, Any] = None,
            notes: str = ""
        ):
            success = self.pipeline.review_quarantined_record(
                batch_id, record_id, reviewer, action, corrected_data, notes
            )
            return {
                'success': success,
                'message': 'Review completed successfully' if success else 'Review failed'
            }
        return review_handler