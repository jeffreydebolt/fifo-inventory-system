#!/usr/bin/env python3
"""
Test the FIFO API endpoints locally
"""
import requests
import sys

API_BASE = "http://localhost:8000"

def test_upload_and_fifo():
    """Test file upload and FIFO calculation locally"""
    
    # Test health endpoint
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"API not running: {e}")
        return False
    
    # Upload lots file
    lots_file_path = "/Users/jeffreydebolt/Downloads/lots_template (1).csv"
    try:
        with open(lots_file_path, 'rb') as f:
            files = {'file': f}
            data = {'tenant_id': 'test_tenant'}
            response = requests.post(f"{API_BASE}/api/v1/files/lots", files=files, data=data)
            print(f"Lots upload: {response.status_code}")
            lots_result = response.json()
            print(f"Lots result: {lots_result}")
            lots_file_id = lots_result['file_id']
    except Exception as e:
        print(f"Lots upload failed: {e}")
        return False
    
    # Upload sales file 
    sales_file_path = "/Users/jeffreydebolt/Downloads/july_sales_convertedtest.csv"
    try:
        with open(sales_file_path, 'rb') as f:
            files = {'file': f}
            data = {'tenant_id': 'test_tenant'}
            response = requests.post(f"{API_BASE}/api/v1/files/sales", files=files, data=data)
            print(f"Sales upload: {response.status_code}")
            sales_result = response.json()
            print(f"Sales result: {sales_result}")
            sales_file_id = sales_result['file_id']
    except Exception as e:
        print(f"Sales upload failed: {e}")
        return False
    
    # Run FIFO calculation
    try:
        payload = {
            'tenant_id': 'test_tenant',
            'lots_file_id': lots_file_id,
            'sales_file_id': sales_file_id
        }
        response = requests.post(f"{API_BASE}/api/v1/runs", json=payload)
        print(f"FIFO run: {response.status_code}")
        fifo_result = response.json()
        print(f"FIFO result: {fifo_result}")
        
        if fifo_result.get('status') == 'completed':
            print(f"✅ FIFO calculation successful!")
            print(f"   Sales processed: {fifo_result.get('total_sales_processed')}")
            print(f"   Total COGS: ${fifo_result.get('total_cogs_calculated')}")
            return True
        else:
            print(f"❌ FIFO calculation failed")
            if fifo_result.get('error'):
                print(f"   Error: {fifo_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"FIFO run failed: {e}")
        return False

if __name__ == "__main__":
    success = test_upload_and_fifo()
    sys.exit(0 if success else 1)