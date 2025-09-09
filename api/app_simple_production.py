"""
Simple, production-ready FastAPI application for FIFO COGS system.
"""
import os
import logging
from datetime import datetime
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

# Diagnostic endpoint for debugging database connection
@app.get("/debug/database")
async def debug_database():
    """Debug database connection status"""
    import os
    from api.services.supabase_service import supabase_service
    
    # Force reinitialize to pick up any new environment variables
    supabase_service._init_client()
    
    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "environment_variables": {
            "SUPABASE_URL_exists": bool(os.getenv("SUPABASE_URL")),
            "SUPABASE_URL_length": len(os.getenv("SUPABASE_URL", "")),
            "SUPABASE_SERVICE_ROLE_KEY_exists": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
            "SUPABASE_SERVICE_ROLE_KEY_length": len(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
            "PYTHONPATH": os.getenv("PYTHONPATH", "not set"),
        },
        "supabase_client_status": supabase_service.supabase is not None,
    }
    
    # Test database connection
    if supabase_service.supabase:
        try:
            # Try a simple table read
            result = supabase_service.supabase.table('uploaded_files').select("*").limit(1).execute()
            diagnostics["database_test"] = {
                "status": "success",
                "rows_returned": len(result.data),
                "error": None
            }
        except Exception as e:
            diagnostics["database_test"] = {
                "status": "failed",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error": None if not str(e) else str(e)
            }
    else:
        diagnostics["database_test"] = {
            "status": "no_client",
            "error": "Supabase client not initialized"
        }
    
    return diagnostics

# Include routers - import here to avoid circular imports
try:
    from api.routes.files import router as files_router
    from api.routes.runs import router as runs_router
    
    app.include_router(files_router, prefix="/api/v1")
    app.include_router(runs_router, prefix="/api/v1")
    
    logging.info("Successfully loaded API routes")
except Exception as e:
    logging.error(f"Failed to load API routes: {e}")

# Initialize Supabase on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    from api.services.supabase_service import supabase_service
    logging.info("Initializing Supabase connection...")
    # This will trigger the connection attempt and log the results
    if supabase_service.supabase:
        logging.info("✅ Supabase client is initialized")
    else:
        logging.warning("⚠️ Supabase client is NOT initialized - running in demo mode")

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