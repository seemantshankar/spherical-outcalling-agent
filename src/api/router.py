from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
import tempfile
import os
import hashlib
from typing import Optional, cast, Dict, Any, List
from sqlalchemy.orm import Session
from src.api.schemas import SpecQueryRequest, SpecQueryResponse, ExtendedSpecQueryResponse, CrossSellSuggestion, CampaignMetadataResponse
from src.storage.database import get_db

from src.spherical_extract import SphericalExtractor
from src.spherical_retrieval import SphericalRetrievalEngine

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

@router.post("/upload")
async def upload_brochure(
    file: UploadFile = File(...),
    oem_id: str = Form(...),
    campaign_id: str = Form(...),
    model_code: str = Form(...),
    model_year: int = Form(...),
    region: str = Form(...),
    engine_code: str = Form(...),
    transmission: str = Form(...),
    fuel_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Ingests a raw brochure PDF, processes its layout, and extracts variant features to the database.
    """
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    # Save the file temporarily
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        content = await file.read()
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            
        # Use library for ingestion
        extractor = SphericalExtractor(db_session=db)
        
        # Format the single configuration into the new batch format
        configs = [{
            "engine": engine_code,
            "trans": transmission,
            "fuel": fuel_type
        }]

        extracted_facts = extractor.ingest_brochure(
            filepath=temp_path,
            oem_id=oem_id,
            campaign_id=campaign_id,
            model_code=model_code,
            model_year=model_year,
            region=region,
            configs=configs
        )
        
        if not extracted_facts:
            return {"status": "warning", "message": "No specific table facts could be reliably extracted from this layout."}
            
        return {
            "status": "success", 
            "message": f"Successfully ingested {len(extracted_facts)} variant configurations from {file.filename}."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        os.remove(temp_path)

@router.get("/metadata", response_model=CampaignMetadataResponse)
def get_campaign_metadata(
    oem_id: str,
    campaign_id: str,
    model_code: str,
    db: Session = Depends(get_db)
):
    """
    Returns unique variants and configurations for a campaign to populate UI dropdowns.
    """
    engine = SphericalRetrievalEngine(db_session=db)
    metadata = engine.get_campaign_metadata(oem_id, campaign_id, model_code)
    return metadata

@router.post("/query", response_model=ExtendedSpecQueryResponse)
def query_spec(request: SpecQueryRequest, db: Session = Depends(get_db)):
    """
    Primary endpoint for Voice Agents to fetch a specific vehicle feature.
    Phase 1: Requires all variant configurations to be present or uses basic inference.
    """
    engine = SphericalRetrievalEngine(db_session=db)
    
    try:
        response = engine.query_spec(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
