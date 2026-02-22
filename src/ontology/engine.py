class OntologyEngine:
    """
    Phase 1: Static mapping of terminology to normalize structural extractions.
    Ensures that various nomenclatures across brochures (e.g., 'milage' vs 'fuel_efficiency')
    are routed to a single determinant taxonomy. Also handles template generation for voice agents.
    """
    
    CORE_FEATURES = {
        "fuel_efficiency": {
            "synonyms": ["mileage", "fuel economy", "milage"],
            "template": "The certified mileage is {value} {unit}.",
            "category": "performance"
        },
        "power_windows": {
            "synonyms": ["electric windows", "auto windows", "power glass"],
            "template": "Power windows are {value}.",
            "category": "comfort_convenience"
        },
        "water_wading": {
            "synonyms": ["wading depth", "water wading depth"],
            "template": "The water wading depth is {value} {unit}.",
            "category": "capability"
        },
        "dual_tone_exterior": {
            "synonyms": ["dual tone", "two tone roof"],
            "template": "The dual tone exterior is {value}.",
            "category": "exterior"
        },
        "overall_length": {
            "synonyms": ["length"],
            "template": "The overall length is {value} {unit}.",
            "category": "dimensions"
        }
    }
    
    @classmethod
    def resolve_feature_id(cls, raw_term: str) -> str:
        """Resolves a raw brochure term into a standardized feature_id."""
        normalized = raw_term.lower().strip()
        
        if normalized in cls.CORE_FEATURES:
            return normalized
            
        for f_id, f_data in cls.CORE_FEATURES.items():
            if normalized in f_data["synonyms"]:
                return f_id
                
        # Unreviewed term extension mechanism
        return f"ext_unreviewed_{normalized.replace(' ', '_')}"
        
    @classmethod
    def render_template(cls, feature_id: str, value_json: dict) -> str:
        """Converts structured JSON data into a voice-friendly context string."""
        feature_meta = cls.CORE_FEATURES.get(feature_id)
        
        value = value_json.get("numeric", value_json.get("text", value_json.get("scope", "unknown")))
        unit = value_json.get("unit", "")
        
        if not feature_meta:
            # Fallback formatting for unreviewed extensions
            return f"The value for {feature_id.replace('ext_unreviewed_', '').replace('_', ' ')} is {value} {unit}."
            
        template = str(feature_meta["template"])
        return template.format(value=value, unit=unit).strip()
