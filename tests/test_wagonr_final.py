import sys
import logging

logging.basicConfig(level=logging.INFO)

from src.spherical_extract.ingestion.extractor import classify_pdf_pages, process_brochure

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"

try:
    facts = process_brochure(
        filepath=pdf_path,
        oem_id="maruti_suzuki",
        campaign_id="c1",
        model_code="wagonr",
        model_year=2024,
        region="IN",
        engine_code="K12N",
        transmission="AMT",
        fuel_type="petrol",
        doc_type="brochure"
    )
    
    print(f"\nSuccessfully extracted {len(facts)} facts via Vision LLM.")
    for f in facts[:10]:
        print(f"{f.trim} - {f.category}/{f.feature_id}: {f.availability_state.name} ({f.precomputed_value_display})")
except Exception as e:
    print(f"Extraction failed: {e}")

