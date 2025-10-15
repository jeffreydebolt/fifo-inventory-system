import os
import sys

sys.path.append('/app')

from api.app import app  # Canonical FastAPI application
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting FIFO COGS API on port {port} using api.app")
    uvicorn.run(app, host="0.0.0.0", port=port)
