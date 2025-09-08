"""
Simple, production-ready FastAPI application for FIFO COGS system.
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="FIFO COGS API",
    description="Multi-tenant FIFO COGS calculation system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fifo-cogs-beta.netlify.app",
        "https://app.firstlot.co",
        "https://*.netlify.app",
        "*"  # Allow all origins for now
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fifo-cogs-api"}

# Include routers - import here to avoid circular imports
try:
    from api.routes.files import router as files_router
    from api.routes.runs import router as runs_router
    
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    
    logging.info("Successfully loaded API routes")
except Exception as e:
    logging.error(f"Failed to load API routes: {e}")

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logging.info(f"Starting FIFO COGS API on {host}:{port}")
    
    uvicorn.run(
        "api.app_simple_production:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )