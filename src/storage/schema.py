import enum
from sqlalchemy import Column, Integer, String, Float, Enum, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class AvailabilityState(str, enum.Enum):
    standard = "standard"
    optional = "optional"
    not_available = "not_available"
    not_mentioned = "not_mentioned"

class SpecFact(Base):
    """
    Core denormalized table for O(1) retrieval of vehicle configuration facts.
    Each row represents a single feature fact for a specific derived variant.
    """
    __tablename__ = "spec_facts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Deterministic Hash of (oem_id, model_code, model_year, trim, engine_code, transmission, fuel_type, region)
    derived_variant_id = Column(String, nullable=False)
    
    # Structural Axes (Explicit Columns for Future-Proofing)
    oem_id = Column(String, nullable=False)
    campaign_id = Column(String, nullable=False)
    model_code = Column(String, nullable=False)
    model_year = Column(Integer, nullable=False)
    region = Column(String, nullable=False)
    trim = Column(String, nullable=True)                            # e.g., 'VXi', 'ZXi'
    engine_code = Column(String, nullable=True)                     # e.g., 'K12N'
    transmission = Column(String, nullable=True)                    # e.g., 'MT', 'AMT'
    fuel_type = Column(String, nullable=True)                       # e.g., 'petrol', 'CNG'
    drive_type = Column(String, default='FWD', nullable=False)      # e.g., 'FWD', 'AWD'

    # Feature Identity (Ontology-Bound)
    feature_id = Column(String, nullable=False)                     # e.g., 'fuel_efficiency'
    category = Column(String, nullable=False)                       # e.g., 'performance'

    # Value & State
    value_json = Column(JSONB, nullable=False, default=dict)
    availability_state = Column(Enum(AvailabilityState), nullable=False)

    # Trust & Audit 
    source_doc_id = Column(String, nullable=False)
    source_page = Column(Integer, nullable=False)
    source_priority = Column(Integer, nullable=False)
    extraction_confidence = Column(Float, nullable=False)

    # Retrieval Optimization (Denormalized)
    search_keywords = Column(ARRAY(String), nullable=True)
    precomputed_value_display = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'oem_id', 'model_code', 'model_year', 'trim', 'engine_code', 
            'transmission', 'fuel_type', 'region', 'feature_id',
            name='uq_variant_config_feature'
        ),
        # Covering index equivalent for fast lookups
        Index('idx_variant_lookup', 'derived_variant_id', 'feature_id'),
        Index('idx_model_filter', 'model_code', 'model_year', 'region', 'feature_id'),
    )

class OntologyFeatureVector(Base):
    """
    Vectorized storage of ontology feature definitions for semantic resolution.
    """
    __tablename__ = "ontology_feature_vectors"
    
    canonical_id = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    description = Column(String, nullable=True)
    embedding = Column(Vector(1536)) # text-embedding-3-small and text-embedding-ada-002 are 1536 dims
