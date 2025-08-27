"""
Minimal FastAPI application for deployment testing.
"""
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import pandas as pd
import io
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="FirstLot FIFO API",
    description="Minimal API for FirstLot MVP",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "FirstLot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "firstlot-api"}

@app.get("/api/v1/files/templates/lots")
async def get_lots_template():
    """Download CSV template for lots upload."""
    template_data = {
        'lot_id': ['LOT001', 'LOT002'],
        'sku': ['SKU-A', 'SKU-B'],
        'received_date': ['2024-01-01', '2024-01-15'],
        'original_quantity': [100, 50],
        'remaining_quantity': [100, 50],
        'unit_price': [10.00, 20.00],
        'freight_cost_per_unit': [1.00, 2.00]
    }
    
    df = pd.DataFrame(template_data)
    csv_content = df.to_csv(index=False)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lots_template.csv"}
    )

@app.get("/api/v1/files/templates/sales")
async def get_sales_template():
    """Download CSV template for sales upload."""
    template_data = {
        'sku': ['SKU-A', 'SKU-B', 'SKU-A'],
        'units moved': [30, 20, 15],
        'Month': ['January 2024', 'January 2024', 'February 2024']
    }
    
    df = pd.DataFrame(template_data)
    csv_content = df.to_csv(index=False)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_template.csv"}
    )

@app.post("/api/v1/files/lots")
async def upload_lots(
    tenant_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload lots CSV file."""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"Uploaded lots file: {file.filename} ({len(df)} rows)")
        
        return {
            "file_id": "demo_lots_123",
            "tenant_id": tenant_id,
            "filename": file.filename,
            "file_type": "lots",
            "rows_count": len(df),
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload lots file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/v1/files/sales")
async def upload_sales(
    tenant_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload sales CSV file."""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"Uploaded sales file: {file.filename} ({len(df)} rows)")
        
        return {
            "file_id": "demo_sales_123",
            "tenant_id": tenant_id,
            "filename": file.filename,
            "file_type": "sales",
            "rows_count": len(df),
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Failed to upload sales file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.post("/api/v1/runs/process")
async def process_fifo():
    """Process FIFO calculation (demo)."""
    return {
        "run_id": "demo_run_123",
        "status": "completed",
        "message": "Demo FIFO calculation completed",
        "processed_skus": 5,
        "total_cogs": 1234.56
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "api.app_simple:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )