from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
import tempfile
import os
import hashlib
from typing import Optional, cast, Dict, Any, List
from sqlalchemy.orm import Session
from src.api.schemas import SpecQueryRequest, SpecQueryResponse, ExtendedSpecQueryResponse, CrossSellSuggestion
from src.storage.database import get_db
from src.storage.schema import SpecFact

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

OEM_UPGRADE_PATHS = {
    "maruti_suzuki": {
        "wagonr": {
            "next_tier": ["ciaz", "brezza"],
            "reason_tags": ["more_power", "premium_features", "suv_segment"]
        }
    }
}

def generate_variant_hash(oem_id: str, model_code: str, model_year: int, trim: str, engine_code: str, transmission: str, fuel_type: str, region: str) -> str:
    """Deterministic hash generator for O(1) variant lookup."""
    key = f"{oem_id}|{model_code}|{model_year}|{trim}|{engine_code}|{transmission}|{fuel_type}|{region}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def _get_cross_sell(oem_id: str, model_code: str) -> Optional[List[CrossSellSuggestion]]:
    suggestions = None
    if oem_id in OEM_UPGRADE_PATHS and model_code in OEM_UPGRADE_PATHS[oem_id]:
        upgrade_info = OEM_UPGRADE_PATHS[oem_id][model_code]
        suggestions = [
            CrossSellSuggestion(model=m, reason=upgrade_info["reason_tags"][0])
            for m in upgrade_info["next_tier"]
        ]
    return suggestions

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

@router.post("/query", response_model=ExtendedSpecQueryResponse)
def query_spec(request: SpecQueryRequest, db: Session = Depends(get_db)):
    """
    Primary endpoint for Voice Agents to fetch a specific vehicle feature.
    Phase 1: Requires all variant configurations to be present or uses basic inference.
    """
    # 1. Config Resolution Engine Logic: Infer missing parameters 
    inferred_trim = request.trim
    inferred_engine = request.engine_code
    inferred_trans = request.transmission
    inferred_fuel = request.fuel_type
    
    valid_config = None
    if not all([inferred_trim, inferred_engine, inferred_trans, inferred_fuel]):
        # Phase 1 Config Resolution: Find first available config for this model
        valid_config = db.query(SpecFact).filter(
            SpecFact.oem_id == request.oem_id,
            SpecFact.campaign_id == request.campaign_id,
            SpecFact.model_code == request.model_code,
            SpecFact.model_year == request.model_year,
            SpecFact.region == request.region
        ).first()
        
    if not valid_config:
        # If we failed to find any valid_config, we cannot logically infer missing dimensions from None.
        if not all([request.trim, request.engine_code, request.transmission, request.fuel_type]):
            raise HTTPException(status_code=400, detail="Missing configuration: Could not resolve valid baseline configuration.")

    if valid_config:
        inferred_trim = inferred_trim or cast(str, valid_config.trim)
        inferred_engine = inferred_engine or cast(str, valid_config.engine_code)
        inferred_trans = inferred_trans or cast(str, valid_config.transmission)
        inferred_fuel = inferred_fuel or cast(str, valid_config.fuel_type)

    if not inferred_trim or not inferred_engine or not inferred_trans or not inferred_fuel:
        raise HTTPException(status_code=400, detail="Missing configuration: Dimensions could not be resolved.")

    derived_variant_id = generate_variant_hash(
        request.oem_id, request.model_code, request.model_year, inferred_trim,
        inferred_engine, inferred_trans, inferred_fuel, request.region
    )

    from src.storage.cache import get_spec_from_cache, set_spec_in_cache
    from src.ontology.engine import OntologyEngine

    resolved_feature_id = OntologyEngine.resolve_feature_id(request.feature_id)

    # 1. Redis Cache Lookup (O(1) optimal path)
    cached_fact = get_spec_from_cache(derived_variant_id, resolved_feature_id)
    if cached_fact:
        # Cache Hit
        answer_text = OntologyEngine.render_template(resolved_feature_id, cached_fact["value_json"])
        confidence = "high" if cached_fact["extraction_confidence"] >= 0.95 else "medium"
        return ExtendedSpecQueryResponse(
            answer=answer_text,
            citation=f"According to page {cached_fact['source_page']} of the {cached_fact.get('source_doc_id', 'brochure')}",
            confidence=confidence,
            source={
                "document": cached_fact.get("source_doc_id", "cache"),
                "page": cached_fact["source_page"],
                "extraction_confidence": cached_fact["extraction_confidence"]
            },
            spec_details={
                "feature": resolved_feature_id,
                "availability_state": cached_fact["availability_state"],
                "value": cached_fact["value_json"]
            },
            cross_sell_suggestions=_get_cross_sell(request.oem_id, request.model_code)
        )

    # 2. Cache Miss - PostgreSQL Lookup with Tenant Isolation
    fact = db.query(SpecFact).filter(
        SpecFact.oem_id == request.oem_id,
        SpecFact.campaign_id == request.campaign_id,
        SpecFact.derived_variant_id == derived_variant_id,
        SpecFact.feature_id == resolved_feature_id
    ).first()

    # Fallback Query Path
    if not fact:
        fallback_terms = [resolved_feature_id]
        if resolved_feature_id in OntologyEngine.CORE_FEATURES:
            fallback_terms.extend(OntologyEngine.CORE_FEATURES[resolved_feature_id].get("synonyms", []))
            
        fact = db.query(SpecFact).filter(
            SpecFact.oem_id == request.oem_id,
            SpecFact.campaign_id == request.campaign_id,
            SpecFact.derived_variant_id == derived_variant_id,
            SpecFact.feature_id.in_(fallback_terms)
        ).first()

    if not fact:
        raise HTTPException(status_code=404, detail="Feature details not found for this variant.")

    # 3. Populate Cache
    value_json_dict = cast(Dict[str, Any], fact.value_json)
    availability_state_val = str(fact.availability_state.value) if hasattr(fact.availability_state, 'value') else str(fact.availability_state)
    source_page_int = cast(int, fact.source_page)
    source_doc_id_str = cast(str, fact.source_doc_id)
    extraction_conf_float = cast(float, fact.extraction_confidence)
    feature_id_str = cast(str, fact.feature_id)

    payload = {
        "value_json": value_json_dict,
        "availability_state": availability_state_val,
        "source_page": source_page_int,
        "source_doc_id": source_doc_id_str,
        "extraction_confidence": extraction_conf_float,
        "precomputed_value_display": cast(Optional[str], fact.precomputed_value_display)
    }
    set_spec_in_cache(derived_variant_id, resolved_feature_id, payload)

    # Generate Voice Response using Ontology Template
    answer_text = OntologyEngine.render_template(resolved_feature_id, value_json_dict)
    confidence = "high" if extraction_conf_float >= 0.95 else ("medium" if feature_id_str == resolved_feature_id else "low")

    return ExtendedSpecQueryResponse(
        answer=answer_text,
        citation=f"According to page {source_page_int} of the {source_doc_id_str}",
        confidence=confidence,
        source={
            "document": source_doc_id_str,
            "page": source_page_int,
            "extraction_confidence": extraction_conf_float
        },
        spec_details={
            "feature": feature_id_str,
            "availability_state": availability_state_val,
            "value": value_json_dict
        },
        cross_sell_suggestions=_get_cross_sell(request.oem_id, request.model_code)
    )
