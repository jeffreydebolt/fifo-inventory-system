#!/usr/bin/env python3
"""
CLIENT CREATION SCRIPT
Quickly set up new clients for beta testing
"""

import os
import json
import hashlib
import secrets
from datetime import datetime

# Simple client storage (file-based for now)
CLIENTS_FILE = "clients.json"

def load_clients():
    """Load existing clients"""
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_clients(clients):
    """Save clients to file"""
    with open(CLIENTS_FILE, 'w') as f:
        json.dump(clients, f, indent=2)

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_client(company_name, email, password=None):
    """Create a new client"""
    
    clients = load_clients()
    
    # Generate client ID from company name
    client_id = company_name.lower().replace(' ', '_').replace('.', '_')
    
    # Remove special characters
    client_id = ''.join(c for c in client_id if c.isalnum() or c == '_')
    
    # Ensure uniqueness
    original_id = client_id
    counter = 1
    while client_id in clients:
        client_id = f"{original_id}_{counter}"
        counter += 1
    
    # Generate password if not provided
    if not password:
        password = secrets.token_urlsafe(12)
    
    # Create client record
    client_data = {
        'client_id': client_id,
        'company_name': company_name,
        'email': email,
        'password_hash': hash_password(password),
        'created_at': datetime.now().isoformat(),
        'status': 'active',
        'uploads_dir': f"client_uploads/{client_id}",
        'results_dir': f"client_results/{client_id}"
    }
    
    # Create directories
    os.makedirs(client_data['uploads_dir'], exist_ok=True)
    os.makedirs(client_data['results_dir'], exist_ok=True)
    
    # Save client
    clients[client_id] = client_data
    save_clients(clients)
    
    print(f"✅ Client created successfully!")
    print(f"   Company: {company_name}")
    print(f"   Client ID: {client_id}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Uploads: {client_data['uploads_dir']}")
    print(f"   Results: {client_data['results_dir']}")
    
    return client_id, password

def verify_client(client_id, password):
    """Verify client credentials"""
    clients = load_clients()
    
    if client_id not in clients:
        return False
    
    client = clients[client_id]
    password_hash = hash_password(password)
    
    return client['password_hash'] == password_hash

def get_client_info(client_id):
    """Get client information"""
    clients = load_clients()
    return clients.get(client_id)

def list_clients():
    """List all clients"""
    clients = load_clients()
    
    if not clients:
        print("No clients found.")
        return
    
    print(f"{'Client ID':<20} {'Company Name':<30} {'Email':<30} {'Status'}")
    print("-" * 90)
    
    for client_id, client in clients.items():
        print(f"{client_id:<20} {client['company_name']:<30} {client['email']:<30} {client['status']}")

def main():
    """Interactive client creation"""
    print("🏢 FIFO CLIENT CREATION TOOL")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Create new client")
        print("2. List existing clients")
        print("3. Test login")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            print("\n📝 Create New Client")
            company = input("Company name: ").strip()
            email = input("Email: ").strip()
            password = input("Password (leave blank for auto-generate): ").strip() or None
            
            if company and email:
                try:
                    client_id, final_password = create_client(company, email, password)
                    
                    # Save credentials to file for easy reference
                    cred_file = f"client_credentials_{client_id}.txt"
                    with open(cred_file, 'w') as f:
                        f.write(f"Client ID: {client_id}\n")
                        f.write(f"Password: {final_password}\n")
                        f.write(f"Company: {company}\n")
                        f.write(f"Email: {email}\n")
                    
                    print(f"\n📄 Credentials saved to: {cred_file}")
                    
                except Exception as e:
                    print(f"❌ Error creating client: {e}")
            else:
                print("❌ Company name and email are required")
        
        elif choice == '2':
            print("\n📋 Existing Clients")
            list_clients()
        
        elif choice == '3':
            print("\n🔐 Test Login")
            client_id = input("Client ID: ").strip()
            password = input("Password: ").strip()
            
            if verify_client(client_id, password):
                print("✅ Login successful!")
                client_info = get_client_info(client_id)
                print(f"   Company: {client_info['company_name']}")
                print(f"   Email: {client_info['email']}")
            else:
                print("❌ Invalid credentials")
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")

def setup_test_clients():
    """Set up test clients quickly"""
    print("🧪 Setting up test clients...")
    
    test_clients = [
        ("Acme Corp", "test1@acme.com", "test123"),
        ("Beta Industries", "test2@beta.com", "test456")
    ]
    
    for company, email, password in test_clients:
        try:
            client_id, _ = create_client(company, email, password)
            print(f"✅ Created test client: {client_id}")
        except Exception as e:
            print(f"❌ Failed to create {company}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "setup-test":
        setup_test_clients()
    else:
        main()