"""
FastAPI application for FIFO COGS system.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from api.routes.runs import router as runs_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="FIFO COGS API",
    description="Multi-tenant FIFO COGS calculation system with rollback support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fifo-cogs-api"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logging.info("FIFO COGS API starting up...")
    
    # Initialize database connections, etc.
    # db_adapter = create_db_adapter()
    
    logging.info("FIFO COGS API startup complete")

# Shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logging.info("FIFO COGS API shutting down...")
    
    # Clean up resources
    # db_adapter.close()
    
    logging.info("FIFO COGS API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "api.app:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )