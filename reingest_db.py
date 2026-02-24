import sys
import logging
from src.storage.database import SessionLocal
from src.storage.schema import SpecFact
from src.spherical_extract import SphericalExtractor

logging.basicConfig(level=logging.INFO)

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"

db = SessionLocal()
print("Flushing old facts for wagonr_2024_launch...")
db.query(SpecFact).filter(SpecFact.campaign_id == "wagonr_2024_launch").delete()
db.commit()

try:
    extractor = SphericalExtractor(db_session=db)
    facts = extractor.ingest_brochure(
        filepath=pdf_path,
        oem_id="maruti_suzuki",
        campaign_id="wagonr_2024_launch",
        model_code="wagonr",
        model_year=2024,
        region="IN",
        engine_code="K12N",
        transmission="AMT",
        fuel_type="petrol"
    )
    
    print(f"\nSuccessfully extracted and SAVED {len(facts)} facts to Database via Vision LLM.")
except Exception as e:
    db.rollback()
    print(f"Extraction failed: {e}")
finally:
    db.close()
