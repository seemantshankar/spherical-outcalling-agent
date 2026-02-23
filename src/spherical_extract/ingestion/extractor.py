# pyre-ignore-all-errors
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
                if "specification" in text.lower() or "features" in text.lower() or "variant" in text.lower():
                    spec_pages.append(i + 1)
            
            if not spec_pages and len(pdf.pages) > 0:
                logger.info("Classification failed to find keywords. Defaulting to all pages for small document.")
                spec_pages = list(range(1, len(pdf.pages) + 1))
    except Exception as e:
        logger.error(f"Page classification failed: {e}")
        
    logger.info(f"Page classification found specification pages: {spec_pages}")
    if not spec_pages:
        logger.warning("No specification pages found and fallback failed, assuming page 1.")
        spec_pages = [1]
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
    
    pages_str = ",".join(map(str, spec_pages))
    logger.info(f"Parsing tables from pages: {pages_str}")
    tables = parse_tables_from_pdf(filepath, pages=pages_str)
    
    extracted_facts = []
    
    for enum_idx, table in enumerate(tables):
        logger.info(f"Processing Table {enum_idx} on page {table.page}...")
        df = table.df
        logger.info(f"Table DataFrame Snippet: \n{df.head(5)}")
        if df.empty or len(df.columns) < 2:
            logger.warning(f"Table {enum_idx} is empty or has < 2 columns. Skipping.")
            continue
            
        # Simplified Variant matrix flattener algorithm
        # Finding the true header row with variant names (LXi, VXi, etc.)
        # Multi-tiered headers in OEMs usually put variants in row 1, 2, or 3
        # First check if the dataframe's actual columns (from LLM) already contain the variant strings!
        header_row_idx = -1
        col_str = " ".join([str(c) for c in df.columns]).upper()
        
        if "LXI" in col_str or "VXI" in col_str or "ZXI" in col_str or "GRADE" in col_str:
            headers = [str(x) for x in df.columns]
        else:
            headers = []
            for i in range(min(4, len(df))):
                row_vals = df.iloc[i].astype(str).tolist()
                row_str = " ".join(row_vals).upper()
                if "LXI" in row_str or "VXI" in row_str or "ZXI" in row_str or "GRADE" in row_str:
                    header_row_idx = i
                    headers = row_vals
                    break
                
        if not headers:
            headers = [str(x) for x in df.columns]
            
        variants = []
        for i in range(1, len(headers)):
            variants.append(str(headers[i]))
        
        for idx in range(int(header_row_idx) + 1, len(df)):
            row = list(df.iloc[idx].astype(str).tolist())
            raw_feature = str(row[0])
            if not raw_feature.strip() or raw_feature.isupper():
                # Skip secondary section headers like 'INTERIORS'
                continue
                
            feature_id = OntologyEngine.resolve_feature_id(raw_feature)
            category = OntologyEngine._attributes.get(feature_id, {}).get("category", "uncategorized")
            
            import re
            for col_idx, variant_name in enumerate(variants):
                # 'VXi | VXi AGS' -> 'VXi' 
                clean_variant = re.split(r'[\n/|]', str(variant_name))[0].strip()
                if not clean_variant:
                    continue
                    
                cell_val = str(row[int(col_idx) + 1]).strip() if (int(col_idx) + 1) < len(row) else ""
                
                # Check Availability conditions (symbol mapping)
                availability = AvailabilityState.standard
                # In Maruti brochures, checkmarks are often used, or 'x' or '-'
                if cell_val in ['-', 'N', 'No', '', 'x', 'X'] or not cell_val:
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
