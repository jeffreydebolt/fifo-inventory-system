import sys
sys.path.append('/app')

# Use the simple production app to avoid Prometheus conflicts
try:
    from api.app_simple_production import app
    print("Loaded simple production app")
except ImportError as e:
    print(f"Failed to import simple app: {e}")
    # Fallback to original app
    from api.app import app
    print("Fallback to original app")

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)