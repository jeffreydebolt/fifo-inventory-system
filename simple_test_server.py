#!/usr/bin/env python3
"""
Simple test server to verify FIFO functionality
"""
import os
import sys
sys.path.append('/Users/jeffreydebolt/Documents/fifo')

from dotenv import load_dotenv
load_dotenv()

# Force demo mode for testing (after loading .env)
os.environ.pop('SUPABASE_URL', None)
os.environ.pop('SUPABASE_ANON_KEY', None)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Simple FIFO Test API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include our routes
from api.routes.files import router as files_router
from api.routes.runs import router as runs_router

app.include_router(files_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "simple-fifo-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)