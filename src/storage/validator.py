import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.storage.schema import SpecFact, AvailabilityState
from src.ontology.engine import OntologyEngine

logger = logging.getLogger(__name__)

def validate_completeness_for_campaign(db: Session, campaign_id: str):
    """
    Offline validation task run after ingestion.
    Ensures that every derived variant in a campaign has exactly ONE row 
    for EVERY core feature in the ontology. If missing, it backfills a 'not_mentioned' row.
    This guarantees that the O(1) cache lookup during voice agent queries never results in a missing fact.
    """
    
    # 1. Get all unique derived_variant_ids for this campaign
    stmt = select(SpecFact.derived_variant_id).where(SpecFact.campaign_id == campaign_id).distinct()
    variants = db.scalars(stmt).all()
    
    if not variants:
        logger.info(f"No variants found for campaign {campaign_id}")
        return

    # 2. For each variant, ensure all core features exist
    core_features = list(OntologyEngine._attributes.keys())
    
    missing_facts: List[SpecFact] = []
    
    for variant_id in variants:
        # Get existing features for this variant
        existing_stmt = select(SpecFact.feature_id).where(
            SpecFact.campaign_id == campaign_id,
            SpecFact.derived_variant_id == variant_id
        )
        existing_features = set(db.scalars(existing_stmt).all())
        
        # Calculate missing features
        for required_feature in core_features:
            if required_feature not in existing_features:
                # We need to construct a stub row for this variant
                # We can grab the structural axes from any existing row of this variant
                base_row_stmt = select(SpecFact).where(SpecFact.derived_variant_id == variant_id).limit(1)
                base_row = db.scalars(base_row_stmt).first()
                
                if base_row:
                    stub = SpecFact(
                        derived_variant_id=variant_id,
                        oem_id=base_row.oem_id,
                        campaign_id=base_row.campaign_id,
                        model_code=base_row.model_code,
                        model_year=base_row.model_year,
                        region=base_row.region,
                        trim=base_row.trim,
                        engine_code=base_row.engine_code,
                        transmission=base_row.transmission,
                        fuel_type=base_row.fuel_type,
                        drive_type=base_row.drive_type,
                        feature_id=required_feature,
                        category=OntologyEngine._attributes.get(required_feature, {}).get("category", "uncategorized"),
                        value_json={},  # Empty value for unmentioned facts
                        availability_state=AvailabilityState.not_mentioned,
                        source_doc_id="synthetic_completeness_validator",
                        source_page=0,   # Flag indicating this was artificially generated
                        source_priority=999,
                        extraction_confidence=1.0,
                        precomputed_value_display="Not mentioned in brochure"
                    )
                    missing_facts.append(stub)
    
    # 3. Bulk insert missing facts
    if missing_facts:
        db.add_all(missing_facts)
        db.commit()
        logger.info(f"Completeness validator backfilled {len(missing_facts)} missing facts for campaign {campaign_id}.")
    else:
        logger.info(f"Campaign {campaign_id} is already 100% complete.")
