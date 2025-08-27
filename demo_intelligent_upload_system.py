#!/usr/bin/env python3
"""
Comprehensive demonstration of the Intelligent Upload System
Shows how it handles real-world messy data gracefully.
"""

import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.intelligent_upload_pipeline import IntelligentUploadPipeline, UploadAPIIntegration


def demo_complete_pipeline():
    """Demonstrate the complete intelligent upload pipeline"""
    print("🚀 INTELLIGENT UPLOAD SYSTEM DEMONSTRATION")
    print("=" * 80)
    print("This system demonstrates how to handle messy real-world CSV uploads")
    print("without ever losing data or completely failing.")
    print()
    
    # Initialize pipeline
    pipeline = IntelligentUploadPipeline(quarantine_dir="quarantine_demo")
    
    # Test files
    test_files = [
        ("test_data/messy_sales_data.csv", "Messy sales data with various format issues"),
        ("sales_data.csv", "Real sales data from current system"),
        ("lots_to_upload.csv", "Real lots data from current system"),
    ]
    
    for file_path, description in test_files:
        if not Path(file_path).exists():
            print(f"⚠️ Skipping {file_path} - file not found")
            continue
            
        print(f"📁 PROCESSING: {description}")
        print(f"   File: {file_path}")
        print("-" * 60)
        
        # Process through pipeline
        results = pipeline.process_upload(file_path, tenant_id="demo_tenant")
        
        # Show results summary
        print(f"✅ STATUS: {results['status'].upper()}")
        if results['status'] == 'success':
            summary = results['processing_summary']
            print(f"   📊 Total Rows: {summary['total_rows']}")
            print(f"   ✅ Processable: {summary['processable_rows']}")
            print(f"   🏥 Quarantined: {summary['quarantined_rows']}")
            print(f"   📈 Success Rate: {summary['success_rate']:.1%}")
            print(f"   🔍 File Type: {results['file_type']}")
            
            # Show preview status
            preview = results['preview']
            print(f"   🎯 Preview Status: {preview['status']}")
            print(f"   🛡️ Safe to Import: {'Yes' if preview['safe_to_import'] else 'No'}")
            
            # Show actionable steps
            if preview['actionable_steps']:
                print("   📋 Next Steps:")
                for i, step in enumerate(preview['actionable_steps'], 1):
                    print(f"      {i}. {step['title']}: {step['description']}")
            
            # Show quarantine info
            quarantine = results['quarantine']
            if quarantine['batch_id']:
                print(f"   🏥 Quarantine Batch: {quarantine['batch_id']}")
                if quarantine['export_path']:
                    print(f"   📤 Export Path: {quarantine['export_path']}")
            
            # Show sample issues
            if results['issues']['critical_count'] > 0:
                print(f"   ⚠️ Critical Issues: {results['issues']['critical_count']}")
                print("      Sample issues:")
                for issue in results['issues']['sample_issues'][:3]:
                    print(f"        - {issue}")
            
            # Show recommendations
            if results['recommendations']:
                print("   💡 Recommendations:")
                for rec in results['recommendations'][:3]:
                    print(f"      - {rec}")
        
        else:
            print(f"   ❌ Error: {results.get('error', 'Unknown error')}")
        
        print()
    
    # Demonstrate quarantine management
    print("🏥 QUARANTINE MANAGEMENT DEMONSTRATION")
    print("=" * 60)
    
    # Get quarantine statistics
    stats = pipeline.get_quarantine_statistics("demo_tenant")
    print(f"📊 Quarantine Statistics:")
    print(f"   Total Batches: {stats['total_batches']}")
    print(f"   Total Records: {stats['total_records']}")
    print(f"   Quarantined Records: {stats['total_quarantined']}")
    print(f"   Average Quarantine Rate: {stats['average_quarantine_rate']:.1%}")
    
    if stats['reason_breakdown']:
        print("   Quarantine Reasons:")
        for reason, count in stats['reason_breakdown'].items():
            print(f"     - {reason.replace('_', ' ').title()}: {count}")
    
    # List quarantine batches
    batches = pipeline.list_quarantine_batches("demo_tenant")
    if batches:
        print(f"\n📋 Recent Quarantine Batches:")
        for batch in batches[:3]:  # Show first 3
            print(f"   • {batch['filename']} ({batch['batch_id'][:8]}...)")
            print(f"     Created: {batch['created_at']}")
            print(f"     Rate: {batch['quarantine_rate']:.1%} ({batch['quarantined_count']}/{batch['total_records']})")
    
    print()


def demo_api_integration():
    """Demonstrate API integration patterns"""
    print("🔌 API INTEGRATION DEMONSTRATION")
    print("=" * 60)
    print("This shows how to integrate with existing FastAPI/Flask applications.")
    print()
    
    # Initialize pipeline and integration
    pipeline = IntelligentUploadPipeline()
    api_integration = UploadAPIIntegration(pipeline)
    
    # Simulate API upload
    class MockUploadFile:
        def __init__(self, filename: str, file_path: str):
            self.filename = filename
            self.file_path = file_path
            
        @property
        def file(self):
            class MockFile:
                def __init__(self, path):
                    self.path = path
                def read(self):
                    with open(self.path, 'rb') as f:
                        return f.read()
            return MockFile(self.file_path)
    
    # Test with existing sales data
    if Path("sales_data.csv").exists():
        print("📤 Simulating API Upload...")
        mock_file = MockUploadFile("sales_data.csv", "sales_data.csv")
        
        response = api_integration.enhanced_upload_handler(
            mock_file,
            tenant_id="api_demo",
            file_type="sales"
        )
        
        print(f"📥 API Response:")
        print(f"   Status: {response['status']}")
        print(f"   Message: {response['message']}")
        
        if 'summary' in response:
            summary = response['summary']
            print(f"   Summary: {summary['processable_rows']}/{summary['total_rows']} processable")
        
        if 'actionable_steps' in response:
            print(f"   Actions Available: {len(response['actionable_steps'])}")
    
    print("✅ API integration patterns demonstrated")
    print()


def demo_safety_features():
    """Demonstrate safety features that prevent data loss"""
    print("🛡️ SAFETY FEATURES DEMONSTRATION")
    print("=" * 60)
    print("Key safety principles of the intelligent upload system:")
    print()
    
    principles = [
        "🔒 NEVER LOSE DATA: All problematic data is quarantined, never discarded",
        "🔍 TRANSPARENT PROCESSING: Every transformation is logged and reversible",
        "👁️ PREVIEW BEFORE IMPORT: Users see exactly what will be imported",
        "🏥 GRACEFUL DEGRADATION: System handles errors without complete failure",
        "📋 ACTIONABLE FEEDBACK: Clear instructions for fixing issues",
        "🔄 MANUAL OVERRIDE: Users can review and correct quarantined data",
        "📊 FULL TRACEABILITY: Every operation is tracked and auditable",
        "🚫 FAIL SAFE: Critical issues prevent import until resolved"
    ]
    
    for principle in principles:
        print(f"   {principle}")
    
    print()
    print("💡 Benefits over traditional upload systems:")
    print("   • No 'all or nothing' failures that lose good data")
    print("   • Intelligent format detection reduces user errors") 
    print("   • Quarantine system allows fixing data without re-upload")
    print("   • Preview system prevents surprise data imports")
    print("   • Detailed logging helps troubleshoot issues")
    print()


def show_example_integration():
    """Show example code for integrating with existing systems"""
    print("💻 INTEGRATION EXAMPLE CODE")
    print("=" * 60)
    
    example_code = '''
# Example: Integrating with existing FastAPI route
from services.intelligent_upload_pipeline import IntelligentUploadPipeline

# Initialize once at startup
upload_pipeline = IntelligentUploadPipeline(quarantine_dir="./quarantine")

@app.post("/upload/sales")
async def upload_sales_enhanced(
    tenant_id: str = Form(...),
    file: UploadFile = File(...)
):
    # Process through intelligent pipeline
    results = upload_pipeline.process_upload(
        file_path=file.filename,  # Save file first
        tenant_id=tenant_id,
        filename=file.filename
    )
    
    if results['preview']['safe_to_import']:
        # Can import immediately - data is clean
        normalized_data = results['normalized_data']
        # ... proceed with existing FIFO calculation
        return {"status": "imported", "rows": len(normalized_data)}
    
    elif results['preview']['requires_review']:
        # Need user review before import
        return {
            "status": "needs_review",
            "quarantine_batch": results['quarantine']['batch_id'],
            "export_csv": results['quarantine']['export_path'],
            "actionable_steps": results['preview']['actionable_steps']
        }
    
    else:
        # Critical issues prevent import
        return {
            "status": "cannot_import", 
            "issues": results['issues'],
            "recommendations": results['recommendations']
        }

@app.post("/quarantine/review")
async def review_quarantine(
    batch_id: str,
    record_id: str,
    action: str,  # 'approve', 'reject', 'fix'
    corrected_data: dict = None
):
    success = upload_pipeline.review_quarantined_record(
        batch_id, record_id, "user_id", action, corrected_data
    )
    
    if success and action == 'approve':
        # Get approved data ready for import
        ready_data = upload_pipeline.get_import_ready_data(batch_id)
        # ... proceed with FIFO calculation
    
    return {"success": success}
'''
    
    print(example_code)


def main():
    """Run complete demonstration"""
    print("🎯 INTELLIGENT UPLOAD SYSTEM - COMPLETE DEMONSTRATION")
    print("This system gracefully handles messy real-world CSV uploads")
    print("without ever completely failing or losing data.")
    print("\n" + "=" * 80 + "\n")
    
    # Run demonstrations
    demo_complete_pipeline()
    demo_api_integration() 
    demo_safety_features()
    show_example_integration()
    
    print("=" * 80)
    print("✅ DEMONSTRATION COMPLETE")
    print()
    print("🎉 SUMMARY:")
    print("The Intelligent Upload System provides:")
    print("• Automatic format detection and column mapping")
    print("• Graceful handling of messy real-world data")
    print("• Preview system showing exactly what will be imported")
    print("• Quarantine system that never loses problematic data")
    print("• Clear actionable feedback for fixing issues")
    print("• Complete integration with existing FIFO systems")
    print()
    print("🚀 Ready for production deployment!")


if __name__ == "__main__":
    main()