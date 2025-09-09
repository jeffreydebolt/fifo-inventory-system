"""Test Supabase connection with production credentials"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def test_connection():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"Testing Supabase connection...")
    print(f"URL: {url[:30]}..." if url else "URL not found")
    print(f"Service Role Key: {key[:30]}..." if key else "Service Role Key not found")
    print(f"Key format check - starts with 'eyJ': {key.startswith('eyJ') if key else False}")
    print(f"Key format check - starts with 'sb_': {key.startswith('sb_') if key else False}")
    
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    try:
        # Create client
        client = create_client(url, key)
        print("✅ Client created successfully")
        
        # Test with a simple query
        result = client.table('uploaded_files').select("*").limit(1).execute()
        print(f"✅ Query successful, returned {len(result.data)} rows")
        
        # Test insert (then delete)
        import uuid
        test_id = str(uuid.uuid4())
        test_data = {
            'file_id': test_id,
            'tenant_id': 'test_tenant',
            'filename': 'test.csv',
            'file_type': 'csv',
            'file_size': 100,
            'uploaded_at': '2025-01-09T12:00:00',
            'processed': False
        }
        
        insert_result = client.table('uploaded_files').insert(test_data).execute()
        print("✅ Insert test successful")
        
        # Clean up
        delete_result = client.table('uploaded_files').delete().eq('file_id', test_id).execute()
        print("✅ Delete test successful")
        
        print("\n✅ All tests passed! Database connection is working.")
        
    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()