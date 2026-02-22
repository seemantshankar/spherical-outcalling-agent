from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
import tempfile
import os
import hashlib
from sqlalchemy.orm import Session
from src.api.schemas import SpecQueryRequest, SpecQueryResponse
from src.storage.database import get_db
from src.storage.schema import SpecFact

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

def generate_variant_hash(oem_id: str, model_code: str, model_year: int, trim: str, engine_code: str, transmission: str, fuel_type: str, region: str) -> str:
    """Deterministic hash generator for O(1) variant lookup."""
    key = f"{oem_id}|{model_code}|{model_year}|{trim}|{engine_code}|{transmission}|{fuel_type}|{region}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

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
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    # Save the file temporarily
    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        content = await file.read()
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            
        # Process the brochure using the extraction pipeline
        from src.ingestion.extractor import process_brochure
        extracted_facts = process_brochure(
            filepath=temp_path,
            oem_id=oem_id,
            campaign_id=campaign_id,
            model_code=model_code,
            model_year=model_year,
            region=region,
            engine_code=engine_code,
            transmission=transmission,
            fuel_type=fuel_type
        )
        
        if not extracted_facts:
            return {"status": "warning", "message": "No specific table facts could be reliably extracted from this layout."}
            
        # Bulk insert into database
        db.add_all(extracted_facts)
        db.commit()
        
        # Run completeness validator to ensure query stability
        from src.storage.validator import validate_completeness_for_campaign
        validate_completeness_for_campaign(db, campaign_id)
        
        return {
            "status": "success", 
            "message": f"Successfully ingested {len(extracted_facts)} variant configurations from {file.filename}."
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        os.remove(temp_path)

@router.post("/query", response_model=SpecQueryResponse)
def query_spec(request: SpecQueryRequest, db: Session = Depends(get_db)):
    """
    Primary endpoint for Voice Agents to fetch a specific vehicle feature.
    Phase 1: Requires all variant configurations to be present or uses basic inference.
    """
    # [TO-DO] Config Resolution Engine Logic: Infer missing parameters 
    inferred_trim = request.trim
    inferred_engine = request.engine_code
    inferred_trans = request.transmission
    inferred_fuel = request.fuel_type
    
    if not all([inferred_trim, inferred_engine, inferred_trans, inferred_fuel]):
        # Simple Phase 1 default/fallback logic could be implemented here
        # E.g., defaulting to the highest volume trim if missing
        pass

    # Ensure we have all necessary parts built 
    # (If we don't, we return a clarification request or 400 Bad Request if missing critical dimensions)
    if not inferred_trim:
        raise HTTPException(status_code=400, detail="Missing configuration: Trim could not be resolved.")

    derived_variant_id = generate_variant_hash(
        request.oem_id, request.model_code, request.model_year, inferred_trim,
        inferred_engine, inferred_trans, inferred_fuel, request.region
    )

    # 1. Redis Cache Lookup (O(1) optimal path)
    from src.storage.cache import get_spec_from_cache, set_spec_in_cache
    from src.ontology.engine import OntologyEngine

    cached_fact = get_spec_from_cache(derived_variant_id, request.feature_id)
    if cached_fact:
        # Cache Hit
        answer_text = OntologyEngine.render_template(request.feature_id, cached_fact["value_json"])
        confidence = "high" if cached_fact["extraction_confidence"] >= 0.95 else "medium"
        return SpecQueryResponse(
            answer=answer_text,
            citation=f"According to page {cached_fact['source_page']} of the {cached_fact['source_doc_id']}",
            confidence=confidence,
            source={
                "document": cached_fact["source_doc_id"],
                "page": cached_fact["source_page"],
                "extraction_confidence": cached_fact["extraction_confidence"]
            },
            spec_details={
                "feature": request.feature_id,
                "availability_state": cached_fact["availability_state"],
                "value": cached_fact["value_json"]
            }
        )

    # 2. Cache Miss - PostgreSQL Lookup
    fact = db.query(SpecFact).filter(
        SpecFact.derived_variant_id == derived_variant_id,
        SpecFact.feature_id == request.feature_id
    ).first()

    if not fact:
        raise HTTPException(status_code=404, detail="Feature details not found for this variant.")

    # 3. Populate Cache
    payload = {
        "value_json": fact.value_json,
        "availability_state": fact.availability_state.value,
        "source_page": fact.source_page,
        "source_doc_id": fact.source_doc_id,
        "extraction_confidence": fact.extraction_confidence,
        "precomputed_value_display": fact.precomputed_value_display
    }
    set_spec_in_cache(derived_variant_id, request.feature_id, payload)

    # Generate Voice Response using Ontology Template
    answer_text = OntologyEngine.render_template(request.feature_id, fact.value_json)
    confidence = "high" if fact.extraction_confidence >= 0.95 else "medium"

    return SpecQueryResponse(
        answer=answer_text,
        citation=f"According to page {fact.source_page} of the {fact.source_doc_id}",
        confidence=confidence,
        source={
            "document": fact.source_doc_id,
            "page": fact.source_page,
            "extraction_confidence": fact.extraction_confidence
        },
        spec_details={
            "feature": fact.feature_id,
            "availability_state": fact.availability_state,
            "value": fact.value_json
        }
    )
