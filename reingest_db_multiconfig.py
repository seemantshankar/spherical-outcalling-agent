import sys
import logging
from typing import List, Dict

from src.storage.database import SessionLocal
from src.storage.schema import SpecFact
from src.spherical_extract import SphericalExtractor

logging.basicConfig(level=logging.INFO)

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"

db = SessionLocal()
print("Flushing old facts for wagonr_2024_launch...")
db.query(SpecFact).filter(SpecFact.campaign_id == "wagonr_2024_launch").delete()
db.commit()

# The WagonR brochure mentions parameters that intersect differently. 
# While proper RAG would parse dimensions individually, our legacy script takes them centrally.
# We will iterate through the common core powertrain offerings to build the hash matrix:
configs = [
    {"engine": "K10C", "trans": "MT", "fuel": "petrol"},
    {"engine": "K10C", "trans": "AMT", "fuel": "petrol"},
    {"engine": "K10C", "trans": "MT", "fuel": "CNG"},
    {"engine": "K12N", "trans": "MT", "fuel": "petrol"},
    {"engine": "K12N", "trans": "AMT", "fuel": "petrol"}
]

try:
    extractor = SphericalExtractor(db_session=db)
    
    facts = extractor.ingest_brochure(
        filepath=pdf_path,
        oem_id="maruti_suzuki",
        campaign_id="wagonr_2024_launch",
        model_code="wagonr",
        model_year=2024,
        region="IN",
        configs=configs
    )
    
    print(f"\nSuccessfully extracted and SAVED {len(facts)} total cross-matrix facts to Database!")
except Exception as e:
    db.rollback()
    print(f"Extraction failed: {e}")
finally:
    db.close()
