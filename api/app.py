"""
FastAPI application for FIFO COGS system.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from prometheus_client import Counter, Histogram, generate_latest

from api.routes.runs import router as runs_router

# Initialize Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above
    event_level=logging.ERROR  # Send errors as events
)

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[
            FastApiIntegration(auto_enable=True),
            sentry_logging,
        ],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
        release=os.getenv("APP_VERSION", "1.0.0"),
    )

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total', 
    'Total HTTP requests', 
    ['method', 'endpoint', 'status']
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 
    'HTTP request duration in seconds'
)

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
    allow_origins=[
        "http://localhost:3000",  # React development server
        "https://fifo-cogs-dashboard.netlify.app",  # Production frontend
        "https://*.netlify.app"  # Any Netlify subdomain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs_router, prefix="/api/v1")

# Import and include files router
from api.routes.files import router as files_router
app.include_router(files_router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "fifo-cogs-api"}

# Healthz endpoint (standard k8s health check)
@app.get("/healthz")
async def healthz():
    """Standard health check endpoint for monitoring/k8s"""
    return {
        "status": "ok",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "commit": os.getenv("GIT_COMMIT", "unknown")
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(generate_latest())

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Send to Sentry
    if os.getenv("SENTRY_DSN"):
        sentry_sdk.capture_exception(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred"
        }
    )

# Middleware for metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect metrics for requests"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=str(request.url.path),
        status=response.status_code
    ).inc()
    
    return response

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