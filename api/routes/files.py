"""
API routes for file uploads (lots and sales).
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
import logging
import uuid
from datetime import datetime
import pandas as pd
import io

from api.models import RunResponse
from services.journaled_calculator import JournaledCalculator
from core.fifo_engine import FIFOEngine

router = APIRouter(prefix="/files", tags=["files"])
logger = logging.getLogger(__name__)


# Dependency injection
def get_calculator() -> JournaledCalculator:
    """Get journaled calculator instance"""
    engine = FIFOEngine()
    return JournaledCalculator(engine, db_adapter=None)


@router.post("/lots", status_code=201)
async def upload_lots_file(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Upload lots CSV file for a tenant.
    
    Validates CSV format and stores for later use in runs.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read and validate CSV
        contents = await file.read()
        try:
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        
        # Validate required columns
        required_columns = ['lot_id', 'sku', 'received_date', 'original_quantity', 
                          'remaining_quantity', 'unit_price', 'freight_cost_per_unit']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Basic validation
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Store file metadata (in real implementation, would save to database)
        file_id = str(uuid.uuid4())
        
        logger.info(f"Uploaded lots file for tenant {tenant_id}: {file.filename} ({len(df)} rows)")
        
        return {
            "file_id": file_id,
            "tenant_id": tenant_id,
            "filename": file.filename,
            "file_type": "lots",
            "rows_count": len(df),
            "uploaded_at": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload lots file: {e}")
        raise HTTPException(status_code=500, detail="Failed to process file")


@router.post("/sales", status_code=201)
async def upload_sales_file(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Upload sales CSV file for a tenant.
    
    Validates CSV format and stores for later use in runs.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read and validate CSV
        contents = await file.read()
        try:
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        
        # Validate required columns (flexible - we have normalizer)
        if len(df.columns) < 3:
            raise HTTPException(
                status_code=400, 
                detail="CSV must have at least 3 columns (SKU, quantity, date)"
            )
        
        # Basic validation
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Store file metadata (in real implementation, would save to database)
        file_id = str(uuid.uuid4())
        
        logger.info(f"Uploaded sales file for tenant {tenant_id}: {file.filename} ({len(df)} rows)")
        
        return {
            "file_id": file_id,
            "tenant_id": tenant_id,
            "filename": file.filename,
            "file_type": "sales",
            "rows_count": len(df),
            "uploaded_at": datetime.now().isoformat(),
            "status": "uploaded"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload sales file: {e}")
        raise HTTPException(status_code=500, detail="Failed to process file")


@router.get("/templates/lots")
async def get_lots_template():
    """
    Download CSV template for lots upload.
    """
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
    
    # Convert to CSV
    csv_content = df.to_csv(index=False)
    
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lots_template.csv"}
    )


@router.get("/templates/sales")
async def get_sales_template():
    """
    Download CSV template for sales upload.
    """
    template_data = {
        'sku': ['SKU-A', 'SKU-B', 'SKU-A'],
        'units moved': [30, 20, 15],
        'Month': ['January 2024', 'January 2024', 'February 2024']
    }
    
    df = pd.DataFrame(template_data)
    
    # Convert to CSV
    csv_content = df.to_csv(index=False)
    
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_template.csv"}
    )