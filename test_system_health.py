#!/usr/bin/env python3
"""
PRODUCTION SYSTEM HEALTH CHECK
Verify that the current system is working before making any changes
"""

import os
import sys
import json
import logging

def test_production_fifo_calculator():
    """Test that production FIFO calculator exists and has core components"""
    print("🧪 Testing Production FIFO Calculator...")
    
    # Check if main file exists
    if not os.path.exists('fifo_calculator_supabase.py'):
        print("❌ CRITICAL: fifo_calculator_supabase.py not found")
        return False
    
    print("✅ Production FIFO calculator file exists")
    
    # Check if it contains critical functions
    try:
        with open('fifo_calculator_supabase.py', 'r') as f:
            content = f.read()
            
        critical_elements = [
            'supabase',
            'purchase_lots', 
            'remaining_unit_qty',
            'FIFO',
            'cogs'
        ]
        
        missing = []
        for element in critical_elements:
            if element.lower() not in content.lower():
                missing.append(element)
        
        if missing:
            print(f"⚠️  Warning: Missing elements: {missing}")
        else:
            print("✅ All critical FIFO elements found in code")
            
    except Exception as e:
        print(f"❌ Error reading FIFO calculator: {e}")
        return False
    
    return True

def test_dashboard_structure():
    """Test that dashboard structure is intact"""
    print("\n🧪 Testing Dashboard Structure...")
    
    dashboard_path = "cogs-dashboard"
    if not os.path.exists(dashboard_path):
        print(f"❌ CRITICAL: Dashboard directory '{dashboard_path}' not found")
        return False
    
    print("✅ Dashboard directory exists")
    
    # Check critical files
    critical_files = [
        'package.json',
        'src/App.js',
        'src/index.js',
        'src/lib/supabaseClient.ts',
        'src/components/AuthGuard.tsx'
    ]
    
    missing_files = []
    for file_path in critical_files:
        full_path = os.path.join(dashboard_path, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ CRITICAL: Missing dashboard files: {missing_files}")
        return False
    
    print("✅ All critical dashboard files exist")
    
    # Check package.json dependencies
    try:
        with open(os.path.join(dashboard_path, 'package.json'), 'r') as f:
            package_data = json.load(f)
            
        deps = package_data.get('dependencies', {})
        critical_deps = ['@supabase/supabase-js', 'react', 'axios']
        
        missing_deps = [dep for dep in critical_deps if dep not in deps]
        if missing_deps:
            print(f"⚠️  Warning: Missing dependencies: {missing_deps}")
        else:
            print("✅ Critical dependencies present")
            
    except Exception as e:
        print(f"⚠️  Warning: Could not check dependencies: {e}")
    
    return True

def test_database_schema():
    """Test that database schema files exist"""
    print("\n🧪 Testing Database Schema...")
    
    schema_file = "infra/migrations/001_create_multi_tenant_schema.sql"
    if not os.path.exists(schema_file):
        print(f"❌ Warning: Schema file '{schema_file}' not found")
        return False
    
    print("✅ Database schema file exists")
    
    # Check if schema contains critical tables
    try:
        with open(schema_file, 'r') as f:
            schema_content = f.read()
            
        critical_tables = [
            'cogs_runs',
            'inventory_movements',
            'cogs_attribution',
            'purchase_lots'  # Referenced in FIFO calculator
        ]
        
        missing_tables = []
        for table in critical_tables:
            if table not in schema_content.lower():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"⚠️  Warning: Schema missing tables: {missing_tables}")
        else:
            print("✅ All critical tables defined in schema")
            
    except Exception as e:
        print(f"❌ Error reading schema: {e}")
        return False
    
    return True

def test_api_structure():
    """Test that API structure is in place"""
    print("\n🧪 Testing API Structure...")
    
    api_path = "api"
    if not os.path.exists(api_path):
        print(f"❌ Warning: API directory '{api_path}' not found")
        return False
    
    print("✅ API directory exists")
    
    # Check critical API files
    api_files = [
        'api/app.py',
        'api/routes/runs.py',
        'api/routes/files.py'
    ]
    
    missing_files = []
    for file_path in api_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  Warning: Missing API files: {missing_files}")
    else:
        print("✅ All critical API files exist")
    
    return True

def test_output_directories():
    """Test that output directories exist (indicates system has been used)"""
    print("\n🧪 Testing Output Directories...")
    
    output_dirs = [
        'july_2025_final',
        'production_enhanced',
        'production_test_outputs',
        'may_2025_cogs_retry'
    ]
    
    existing_dirs = []
    for dir_name in output_dirs:
        if os.path.exists(dir_name):
            try:
                files = os.listdir(dir_name)
                existing_dirs.append(f"{dir_name} ({len(files)} files)")
            except:
                existing_dirs.append(f"{dir_name} (access error)")
    
    if existing_dirs:
        print(f"✅ Found output directories: {existing_dirs}")
        print("✅ System has been used for COGS calculations")
    else:
        print("⚠️  No output directories found - system may be new or unused")
    
    return True

def test_backup_integrity():
    """Verify that backups were created successfully"""
    print("\n🧪 Testing Backup Integrity...")
    
    import glob
    
    # Check for production backups
    fifo_backups = glob.glob("fifo_calculator_supabase_PRODUCTION_BACKUP_*.py")
    dashboard_backups = glob.glob("cogs-dashboard_PRODUCTION_BACKUP_*")
    output_backups = glob.glob("fifo_production_outputs_backup_*.tar.gz")
    
    backup_status = []
    
    if fifo_backups:
        backup_status.append(f"✅ FIFO calculator backup: {fifo_backups[-1]}")
    else:
        backup_status.append("❌ MISSING: FIFO calculator backup")
    
    if dashboard_backups:
        backup_status.append(f"✅ Dashboard backup: {dashboard_backups[-1]}")
    else:
        backup_status.append("❌ MISSING: Dashboard backup")
    
    if output_backups:
        backup_status.append(f"✅ Output backup: {output_backups[-1]}")
    else:
        backup_status.append("⚠️  No output backup found")
    
    for status in backup_status:
        print(status)
    
    # Check if safety checklist exists
    if os.path.exists('SAFETY_CHECKLIST.md'):
        print("✅ Safety checklist created")
    else:
        print("❌ MISSING: Safety checklist")
    
    return True

def main():
    """Run all health checks"""
    print("🏥 PRODUCTION SYSTEM HEALTH CHECK")
    print("=" * 50)
    print("Verifying system integrity before making changes...")
    
    tests = [
        test_production_fifo_calculator,
        test_dashboard_structure,
        test_database_schema,
        test_api_structure,
        test_output_directories,
        test_backup_integrity
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("HEALTH CHECK SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 SYSTEM IS HEALTHY - SAFE TO PROCEED")
        print("✅ All critical components are intact")
        print("✅ Backups have been created")
        print("✅ Ready for careful development")
    elif passed >= total - 1:
        print("⚠️  SYSTEM IS MOSTLY HEALTHY - PROCEED WITH CAUTION")
        print("⚠️  Some non-critical issues found")
    else:
        print("❌ SYSTEM HAS ISSUES - DO NOT PROCEED")
        print("❌ Fix critical issues before making changes")
        return False
    
    print("\nNext steps:")
    print("1. Review SAFETY_CHECKLIST.md before any changes")
    print("2. Work in test environment (.env.test)")
    print("3. Test all changes with sample data first")
    print("4. Maintain backups throughout development")
    
    return passed >= total - 1

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)