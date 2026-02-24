from .vehicle_ontology_data import VEHICLE_ONTOLOGY
import difflib

class OntologyEngine:
    """
    Phase 1: Dynamic mapping of terminology to normalize structural extractions.
    Ensures that various nomenclatures across brochures (e.g., 'milage' vs 'fuel_efficiency')
    are routed to a single determinant taxonomy using an O(1) fast lookup dict.
    Also handles template generation for voice agents.
    """
    
    _attributes = {}
    _synonym_map = {}

    @classmethod
    def _initialize(cls):
        """Loads the Auto-Generated native dict ontology and builds the O(1) fast-lookup inverted synonym map."""
        if cls._attributes:
            return  # Already loaded

        try:
            cls._attributes = VEHICLE_ONTOLOGY.get('attributes', {})
                
            # Build O(1) synonym router
            for feature_id, feature_data in cls._attributes.items():
                if not feature_data:
                    continue
                
                # Map the canonical canonical_name itself
                cls._synonym_map[feature_id.lower().strip()] = feature_id
                
                # Crucial Fix: Map the literal space-separated version so raw brochure strings can hit it directly
                cls._synonym_map[feature_id.replace('_', ' ').lower().strip()] = feature_id
                
                # Map all declared synonyms
                for synonym in feature_data.get('synonyms', []):
                    # We normalize synonyms at load time for O(1) lookup later
                    cls._synonym_map[synonym.lower().strip()] = feature_id
                    
        except Exception as e:
            print(f"Error loading ontology dict: {e}")
            cls._attributes = {}
            cls._synonym_map = {}

    @classmethod
    def resolve_feature_id(cls, raw_term: str, best_effort_category: str = "uncategorized") -> str:
        """Resolves a raw brochure term into a standardized feature_id using O(1) dict and PGVector."""
        cls._initialize()
        
        normalized = raw_term.lower().strip()
        
        # O(1) Fast path lookup (critical for <200ms latency)
        if normalized in cls._synonym_map:
            return cls._synonym_map[normalized]
            
        # Fallback 1: Strict Fuzzy String Matching (~5ms penalty)
        matches = difflib.get_close_matches(normalized, cls._synonym_map.keys(), n=1, cutoff=0.85)
        if matches:
            return cls._synonym_map[matches[0]]
            
        # Fallback 2: PGVector Semantic Search using OpenRouter Embeddings
        # Solves generic terms like "weight" implicitly resolving to "kerb_weight"
        try:
            import os
            from openai import OpenAI
            from src.storage.database import SessionLocal
            from src.storage.schema import OntologyFeatureVector
            
            api_key = os.environ.get("OPENROUTER_API_KEY")
            embedding_model = os.environ.get("EMBEDDINGS_LLM", "openai/text-embedding-3-small")
            
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            semantic_query = f"Feature: {raw_term}\nCategory: {best_effort_category}"
            
            res = client.embeddings.create(input=[semantic_query], model=embedding_model)
            query_embedding = res.data[0].embedding
            
            db = SessionLocal()
            try:
                # <=>: Cosine distance in pgvector. Distance of 0 means identical, 2 means exactly opposite. 
                # We want distance < 0.4 (similarity > 0.6)
                nearest = db.query(OntologyFeatureVector).order_by(
                    OntologyFeatureVector.embedding.cosine_distance(query_embedding)
                ).first()
                
                # Check distance
                if nearest:
                    distance = db.execute(
                        db.query(OntologyFeatureVector.embedding.cosine_distance(query_embedding))
                        .filter(OntologyFeatureVector.canonical_id == nearest.canonical_id)
                        .statement
                    ).scalar()
                    
                    if distance is not None and distance < 0.4:
                        return str(nearest.canonical_id)
            finally:
                db.close()
        except Exception as e:
            print(f"Vector search fallback failed for '{raw_term}': {e}")
                
        # Fallback 3: Unreviewed term extension mechanism
        return f"ext_unreviewed_{normalized.replace(' ', '_')}"
        
    @classmethod
    def render_template(cls, feature_id: str, value_json: dict) -> str:
        """Converts structured JSON data into a voice-friendly context string."""
        cls._initialize()
        
        feature_meta = cls._attributes.get(feature_id)
        
        value = value_json.get("numeric", value_json.get("text", value_json.get("scope", "unknown")))
        unit = value_json.get("unit", "")
        
        if not feature_meta:
            # Fallback formatting for unreviewed extensions
            clean_id = feature_id.replace('ext_unreviewed_', '').replace('_', ' ')
            return f"The value for {clean_id} is {value} {unit}."
            
        template = str(feature_meta.get("template", f"The {feature_meta.get('canonical_name', feature_id)} is {{value}} {{unit}}."))
        return template.format(value=value, unit=unit).strip()

# Initialize upon import for maximum performance (optional, but good for caching)
OntologyEngine._initialize()
