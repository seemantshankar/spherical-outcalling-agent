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
    def resolve_feature_id(cls, raw_term: str) -> str:
        """Resolves a raw brochure term into a standardized feature_id in O(1) time."""
        cls._initialize()
        
        normalized = raw_term.lower().strip()
        
        # O(1) Fast path lookup (critical for <200ms latency)
        if normalized in cls._synonym_map:
            return cls._synonym_map[normalized]
            
        # Fallback 1: Fuzzy String Matching (~5ms penalty)
        # Handle OCR text errors, trailing spaces, or minor variations (e.g., 'Kerb Weight (kg)' vs 'Kerb Weight')
        matches = difflib.get_close_matches(normalized, cls._synonym_map.keys(), n=1, cutoff=0.75)
        if matches:
            return cls._synonym_map[matches[0]]
            
        # Fallback 2: Substring keyword matching (e.g., 'weight' solving to 'kerb weight')
        # Only trigger token search if the query is substantive (>3 chars)
        if len(normalized) > 3:
            for syn in cls._synonym_map.keys():
                if normalized in syn:
                    return cls._synonym_map[syn]
                
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
