#!/usr/bin/env python3
"""
Test Supabase connection with exact production credentials
"""
import os
from supabase import create_client

# Set the exact credentials
os.environ['SUPABASE_URL'] = 'https://mdjukynmoingazraqyio.supabase.co'
os.environ['SUPABASE_ANON_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1kanVreW5tb2luZ2F6cmFxeWlvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcyNTY4MjIsImV4cCI6MjA2MjgzMjgyMn0.ebRyktrN2kKAsIsrWFI4eWP3YhrbCPTTt54F2CYp06o'

try:
    print("Testing Supabase connection...")
    
    # Create client
    supabase = create_client(
        os.environ['SUPABASE_URL'],
        os.environ['SUPABASE_ANON_KEY']
    )
    print("✓ Client created successfully")
    
    # Test read from uploaded_files table
    print("Testing read from uploaded_files table...")
    result = supabase.table('uploaded_files').select("*").limit(1).execute()
    print(f"✓ Can read from uploaded_files: {len(result.data)} rows returned")
    
    # Test insert
    print("Testing insert into uploaded_files table...")
    test_data = {
        'tenant_id': 'test_connection',
        'filename': 'test.csv',
        'file_type': 'test',
        'file_size': 100
    }
    result = supabase.table('uploaded_files').insert(test_data).execute()
    print(f"✓ Can insert into uploaded_files: {result.data[0]['file_id']}")
    
    # Test cogs_runs table
    print("Testing cogs_runs table...")
    cogs_result = supabase.table('cogs_runs').select("*").limit(1).execute()
    print(f"✓ Can read from cogs_runs: {len(cogs_result.data)} rows returned")
    
    print("\n🎉 ✅ Database connection WORKS PERFECTLY!")
    print("The issue is not with credentials or database - it's with the service initialization")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc()