from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SpecQueryRequest(BaseModel):
    """
    Standard query payload from the Voice Agent representing inferred entities.
    """
    oem_id: str
    campaign_id: str
    model_code: str
    model_year: int
    region: str
    
    # Resolve Pydantic UserWarning for 'model_' protected namespace
    model_config = {
        "protected_namespaces": ()
    }

    # Optional axes (To be inferred if missing)
    trim: Optional[str] = None
    engine_code: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    drive_type: Optional[str] = None
    
    # The feature requested
    feature_id: str

class SpecQueryResponse(BaseModel):
    """
    Response returned to Voice Agent with fully rendered answer and source attribution.
    """
    answer: str
    citation: str
    confidence: str
    
    # Trust metadata
    source: Dict[str, Any]
    
    # Raw spec data if the frontend wants to display a UI card
    spec_details: Dict[str, Any]

class CrossSellSuggestion(BaseModel):
    model: str
    reason: str

class ExtendedSpecQueryResponse(SpecQueryResponse):
    cross_sell_suggestions: Optional[List[CrossSellSuggestion]] = None
