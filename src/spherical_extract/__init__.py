from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.spherical_extract.ingestion.extractor import process_brochure
from src.storage.validator import validate_completeness_for_campaign

class SphericalExtractor:
    """
    Library entry point for parsing car brochures and ingesting data 
    into the Spherical RAG Engine.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def ingest_brochure(
        self,
        filepath: str,
        oem_id: str,
        campaign_id: str,
        model_code: str,
        model_year: int,
        region: str,
        configs: List[Dict[str, Any]],
        doc_type: str = "brochure"
    ) -> List[Any]:
        """
        Ingests a raw brochure PDF, processes its layout, and extracts variant features to the database.
        
        Returns a list of inserted SpecFact objects.
        Raises an Exception if extraction fails.
        """
        try:
            # Process the brochure using the extraction pipeline
            extracted_facts = process_brochure(
                filepath=filepath,
                oem_id=oem_id,
                campaign_id=campaign_id,
                model_code=model_code,
                model_year=model_year,
                region=region,
                configs=configs,
                doc_type=doc_type
            )
            
            if not extracted_facts:
                return []
                
            # Bulk insert into database
            self.db.add_all(extracted_facts)
            self.db.commit()
            
            # Run completeness validator to ensure query stability
            validate_completeness_for_campaign(self.db, campaign_id)
            
            return extracted_facts
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Extraction failed: {str(e)}")
