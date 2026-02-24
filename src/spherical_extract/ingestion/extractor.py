# pyre-ignore-all-errors
import logging
from typing import List
import pandas as pd
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
    Heuristic page classifier to identify technical specification tables.
    Differentiates between marketing banners (e.g. 'Safety Features') and 
    technical matrices (e.g. 'Dimensions', 'Engine', 'Capacities').
    """
    spec_pages = []
    # Keywords that strongly indicate a technical spec table
    high_priority_keywords = ["dimensions", "engine", "capacities", "weights", "transmission", "specifications"]
    # Keywords that are common but can be in marketing banners
    low_priority_keywords = ["features", "variant", "standard", "optional"]
    
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").lower()
                
                # Count high priority hits
                high_hits = sum(1 for k in high_priority_keywords if k in text)
                low_hits = sum(1 for k in low_priority_keywords if k in text)
                
                # Heuristic: 
                # 1. At least one high priority keyword 
                # OR 
                # 2. At least two distinct low priority keywords AND some numerical density
                is_spec = False
                if high_hits >= 1:
                    is_spec = True
                elif low_hits >= 2:
                    # Check for some technical structural markers like (mm) or (kg) or (L)
                    if any(m in text for m in ["(mm)", "(kg)", "(l)", "(cc)"]):
                        is_spec = True
                
                if is_spec:
                    spec_pages.append(i + 1)
            
            if not spec_pages and len(pdf.pages) > 0:
                logger.info("Classification failed to find technical markers. Falling back to all pages.")
                spec_pages = list(range(1, len(pdf.pages) + 1))
    except Exception as e:
        logger.error(f"Page classification failed: {e}")
        
    logger.info(f"Page classification found technical pages: {spec_pages}")
    if not spec_pages:
        spec_pages = [1]
    return spec_pages

def parse_contextual_value(value: str, fuel: str, engine: str, trans: str) -> str:
    import re
    if not any(sep in value for sep in ('/', '|', '\n')):
        return value
    
    parts = re.split(r'[\n/|]', value)
    for p in parts:
        p_clean = p.strip()
        if not p_clean: continue
        
        # Fuel matching
        if fuel.lower() == 'cng' and any(x in p_clean.lower() for x in ('cng', 'water', 'equivalent', '60')):
            return p_clean
        if fuel.lower() == 'petrol' and any(x in p_clean.lower() for x in ('petrol', 'gasoline', '32')):
            return p_clean
            
        # Engine matching (e.g. 1.0L / 1.2L)
        if engine and engine.lower() in p_clean.lower():
            return p_clean
            
        # Transmission matching (e.g. MT / AMT)
        if trans and trans.lower() in p_clean.lower():
            return p_clean
            
    # Default to first part if no match found but it was a split value
    return parts[0].strip() if parts else value

def process_brochure(
    filepath: str, 
    oem_id: str, 
    campaign_id: str, 
    model_code: str, 
    model_year: int,
    region: str,
    configs: List[dict],
    doc_type: str = "brochure"
) -> List[SpecFact]:
    """
    The orchestrator for taking a raw PDF and transforming its tables into flattened SpecFacts.
    Now optimized to handle multiple powertrain configurations in a single pass.
    """
    precedence = SOURCE_PRECEDENCE.get(doc_type, 99)
    spec_pages = classify_pdf_pages(filepath)
    
    pages_str = ",".join(map(str, spec_pages))
    logger.info(f"Parsing tables from pages: {pages_str}")
    tables = parse_tables_from_pdf(filepath, pages=pages_str)
    
    extracted_facts = []
    
    def find_header_row(df_tbl: pd.DataFrame):
        best_idx = -1
        best_score = -1
        best_headers = []
        def score_row(row_vals):
            score = 0
            seen = set()
            for v in row_vals[1:]: 
                v_str = str(v).strip()
                if v_str and v_str not in seen and not v_str.replace('.', '').isdigit() and len(v_str) > 1:
                    score += 1
                    seen.add(v_str)
            return score
            
        col_score = score_row([str(c) for c in df_tbl.columns])
        if col_score > 0:
            best_score = col_score
            df_tbl = df_tbl.fillna('')
            best_headers = [str(c).strip() for c in df_tbl.columns]
            
        for i in range(min(4, len(df_tbl))):
            row_vals = df_tbl.iloc[i].astype(str).tolist()
            r_score = score_row(row_vals)
            if r_score > best_score:
                best_score = r_score
                best_idx = i
                best_headers = row_vals
                
        if not best_headers:
            best_headers = [str(x) for x in df_tbl.columns]
        return best_idx, best_headers

    def unify_variant_names(raw_variants: list) -> dict:
        import json, os
        from openai import OpenAI
        unique_variants = list(set([str(v).strip() for v in raw_variants if str(v).strip() and str(v).strip().lower() not in ('nan', 'none')]))
        if not unique_variants: return {}
        prompt = (
            "You are an automotive AI specializing in vehicle brochure data. Group the following variant headers and identify their canonical MARKETING TRIM names. "
            "A 'Marketing Trim' is a tier like 'LXi', 'VXi', 'ZXi', 'ZXi+', 'Alpha', 'Zeta', 'Premium', etc. "
            "STRICT RULES:\n"
            "1. Remove technical configurations and feature-states from the name (e.g., 'VXi With ESP' becomes 'VXi', 'LXi (O)' becomes 'LXi', 'ZXi+ AMT' becomes 'ZXi+').\n"
            "2. EXCLUDE terms like 'ESP', 'ABS', 'Airbags', 'With ESP', 'Without ESP', 'Manual', 'Automatic', 'CNG' from the canonical name unless they are part of the core brand name.\n"
            "3. If a name ONLY contains technical features (e.g., 'With ESP'), try to map it to the most likely base trim or use 'Standard'.\n"
            "4. The canonical name MUST BE A SUBSTRING of at least one variant in the provided list.\n"
            "Return ONLY a JSON dict mapping raw variant to canonical trim. No markdown. "
            f"Raw variants: {json.dumps(unique_variants)}"
        )
        try:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            model = os.environ.get("LIGHTWEIGHT_VISION_LLM", "openai/gpt-5-nano")
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
            content = str(response.choices[0].message.content).strip()
            if content.startswith("```json"): content = content[7:-3]
            elif content.startswith("```"): content = content[3:-3]
            mapping = json.loads(content)
            
            # Post-processing: Programmatically block any hallucinations
            # A canonical name is ONLY valid if it exists as a substring (case-insensitive) in the unique_variants list
            sanitized_mapping = {}
            for raw, canonical in mapping.items():
                if not isinstance(canonical, str):
                    sanitized_mapping[raw] = raw
                    continue
                
                # Check if this canonical exists as a substring of ANY raw variant
                is_valid = any(canonical.lower() in rv.lower() for rv in unique_variants)
                
                if is_valid:
                    sanitized_mapping[raw] = canonical
                else:
                    logger.warning(f"Blocking LLM hallucination: '{canonical}' is not in input. Falling back to '{raw}'")
                    sanitized_mapping[raw] = raw
            
            return sanitized_mapping
        except Exception as e:
            logger.error(f"Variant unification failed: {e}")
            return {v: v for v in unique_variants}

    all_raw_variants = []
    table_metadata = []
    
    # Pass 1: Discover all headers
    for enum_idx, table in enumerate(tables):
        if table.df.empty or len(table.df.columns) < 2:
            table_metadata.append((table, -1, []))
            continue
            
        h_idx, headers = find_header_row(table.df)
        
        # Determine if we have a Best Effort Category column from the vision LLM
        has_category_col = len(headers) > 1 and "category" in str(headers[1]).lower()
        variant_start_idx = 2 if has_category_col else 1
        
        table_metadata.append((table, h_idx, headers, variant_start_idx))
        all_raw_variants.extend(headers[variant_start_idx:])
        
    unified_variants_map = unify_variant_names(all_raw_variants)
    logger.info(f"Unified variants map: {unified_variants_map}")
    
    # Pass 2: Extract data
    for enum_idx, (table, header_row_idx, headers, variant_start_idx) in enumerate(table_metadata):
        if not headers:
            continue
            
        logger.info(f"Processing Table {enum_idx} on page {table.page}...")
        df = table.df
        
        variants = []
        for i in range(variant_start_idx, len(headers)):
            raw_var = str(headers[i]).strip()
            variants.append(unified_variants_map.get(raw_var, raw_var))
        
        for idx in range(int(header_row_idx) + 1, len(df)):
            row = list(df.iloc[idx].astype(str).tolist())
            raw_feature = str(row[0])
            if not raw_feature.strip() or raw_feature.isupper():
                continue
            
            best_effort_cat = str(row[1]).strip() if variant_start_idx == 2 else "uncategorized"
            
            feature_id = OntologyEngine.resolve_feature_id(raw_feature, best_effort_category=best_effort_cat)
            category = OntologyEngine._attributes.get(feature_id, {}).get("category", "uncategorized")
            
            import re
            for col_idx, variant_name in enumerate(variants):
                clean_variant = str(re.split(r'[\n/|]', str(variant_name))[0]).strip()
                if not clean_variant:
                    continue
                    
                raw_cell_val = str(row[int(col_idx) + variant_start_idx]).strip() if (int(col_idx) + variant_start_idx) < len(row) else ""
                
                # Bulk expansion for all configurations
                for cfg in configs:
                    current_fuel = cfg.get("fuel", "petrol")
                    current_engine = cfg.get("engine", "")
                    current_trans = cfg.get("trans", "")
                    
                    # Context-aware value refinement
                    cell_val = parse_contextual_value(raw_cell_val, fuel=current_fuel, engine=current_engine, trans=current_trans)
                    
                    availability = AvailabilityState.standard
                    if cell_val in ['-', 'N', 'No', '', 'x', 'X'] or not cell_val:
                        availability = AvailabilityState.not_available
                    elif 'O' in cell_val or 'Opt' in cell_val or 'optional' in cell_val.lower():
                        availability = AvailabilityState.optional
                    
                    var_hash = SphericalRetrievalEngine.generate_variant_hash(
                        oem=oem_id, model=model_code, year=model_year,
                        trim=clean_variant, engine=current_engine,
                        trans=current_trans, fuel=current_fuel, region=region
                    )
                    
                    fact = SpecFact(
                        derived_variant_id=var_hash,
                        oem_id=oem_id,
                        campaign_id=campaign_id,
                        model_code=model_code,
                        model_year=model_year,
                        region=region,
                        trim=clean_variant,
                        engine_code=current_engine,
                        transmission=current_trans,
                        fuel_type=current_fuel,
                        drive_type="FWD",
                        feature_id=feature_id,
                        category=category,
                        value_json={"text": cell_val},
                        availability_state=availability,
                        source_doc_id=filepath,
                        source_page=table.page,
                        source_priority=precedence,
                        extraction_confidence=0.80, 
                        precomputed_value_display=cell_val
                    )
                    extracted_facts.append(fact)
                
    deduped = {}
    for fact in extracted_facts:
        key = (fact.derived_variant_id, fact.feature_id)
        if key not in deduped:
            deduped[key] = fact
        else:
            invalid_vals = ['-', 'N', 'No', '', 'x', 'X']
            new_val = str(fact.precomputed_value_display).strip()
            old_val = str(deduped[key].precomputed_value_display).strip()
            # Upgrade fact if previous is missing/empty but new one is populated
            if old_val in invalid_vals and new_val not in invalid_vals:
                deduped[key] = fact
                
    return list(deduped.values())
