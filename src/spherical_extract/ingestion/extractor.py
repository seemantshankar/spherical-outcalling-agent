import logging
from typing import List
from src.spherical_extract.ingestion.parser import parse_tables_from_pdf
from src.ontology.engine import OntologyEngine
from src.spherical_retrieval import SphericalRetrievalEngine
from src.storage.schema import SpecFact, AvailabilityState

logger = logging.getLogger(__name__)

SOURCE_PRECEDENCE = {
    "spec_sheet": 1,
    "brochure": 2,
    "marketing": 3
}

def classify_pdf_pages(filepath: str) -> List[int]:
    """
    Stub for page classification. For the MVP, we utilize pdfplumber to quickly 
    scan textual keywords like 'Specifications' to tag the pages needing strict table parsing.
    """
    spec_pages = []
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                # Simple classifier heuristics
                if "specification" in text.lower() or "features" in text.lower():
                    spec_pages.append(i + 1)
    except Exception as e:
        logger.error(f"Page classification failed: {e}")
        
    return spec_pages

def process_brochure(
    filepath: str, 
    oem_id: str, 
    campaign_id: str, 
    model_code: str, 
    model_year: int,
    region: str,
    engine_code: str,
    transmission: str,
    fuel_type: str,
    doc_type: str = "brochure"
) -> List[SpecFact]:
    """
    The orchestrator for taking a raw PDF and transforming its tables into flattened SpecFacts.
    Follows Phase 1 architecture of exploding inheritance matrices into fully denormalized DB rows.
    """
    precedence = SOURCE_PRECEDENCE.get(doc_type, 99)
    spec_pages = classify_pdf_pages(filepath)
    
    if not spec_pages:
        logger.warning(f"No specification pages found in {filepath}")
        return []
        
    pages_str = ",".join(map(str, spec_pages))
    tables = parse_tables_from_pdf(filepath, pages=pages_str)
    
    extracted_facts = []
    
    for table in tables:
        df = table.df
        if df.empty or len(df.columns) < 2:
            continue
            
        # Simplified Variant matrix flattener algorithm
        # Column 0: Feature name
        # Column 1..N: Trims (LXi, VXi, ZXi)
        headers = df.iloc[0].tolist()
        variants = headers[1:] 
        
        for idx in range(1, len(df)):
            row = df.iloc[idx].tolist()
            raw_feature = row[0]
            if not raw_feature.strip():
                continue
                
            feature_id = OntologyEngine.resolve_feature_id(raw_feature)
            category = OntologyEngine.CORE_FEATURES.get(feature_id, {}).get("category", "uncategorized")
            
            for col_idx, variant_name in enumerate(variants):
                clean_variant = variant_name.strip()
                if not clean_variant:
                    continue
                    
                cell_val = str(row[col_idx + 1]).strip()
                
                # Check Availability conditions (symbol mapping)
                availability = AvailabilityState.standard
                if cell_val in ['-', 'N', 'No', '', 'x', 'X']:
                    availability = AvailabilityState.not_available
                elif 'O' in cell_val or 'Opt' in cell_val or 'optional' in cell_val.lower():
                    availability = AvailabilityState.optional
                
                var_hash = SphericalRetrievalEngine.generate_variant_hash(
                    oem_id=oem_id, model_code=model_code, model_year=model_year,
                    trim=clean_variant, engine_code=engine_code,
                    transmission=transmission, fuel_type=fuel_type, region=region
                )
                
                fact = SpecFact(
                    derived_variant_id=var_hash,
                    oem_id=oem_id,
                    campaign_id=campaign_id,
                    model_code=model_code,
                    model_year=model_year,
                    region=region,
                    trim=clean_variant,
                    engine_code=engine_code,
                    transmission=transmission,
                    fuel_type=fuel_type,
                    drive_type="FWD",
                    feature_id=feature_id,
                    category=category,
                    value_json={"text": cell_val},
                    availability_state=availability,
                    source_doc_id=filepath,
                    source_page=table.page,
                    source_priority=precedence,
                    extraction_confidence=0.80, # Hardcoded flat base confidence 
                    precomputed_value_display=cell_val
                )
                extracted_facts.append(fact)
                
    return extracted_facts
