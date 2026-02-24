import sys, os
from unittest.mock import MagicMock
sys.modules['sqlalchemy'] = MagicMock()
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['pandas'] = MagicMock()

# Now we can safely import from the src root without PyYAML, SQLAlchemy or Pandas
from src.ontology.engine import OntologyEngine

def simulate_pdf_extraction():
    # These represent raw weird terms found in OEM brochure tables spanning multiple marketing terminologies
    raw_pdf_table_cells = [
        "Smartplay Studio",           # OEM Trade mark 1
        "Touchscreen Infotainment",   # Clean generic 
        "Head Unit",                  # Slang
        "Apple CarPlay",              # Another trademark mapped differently
        "Sun Shades",
        "Ticket Holder",
        "AC", 
        "River Crossing",
        "Unrecognized Marketing Fluff", # Testing fallback mechanism
        "17.78 cm smartplay studio with smartphone navigation",
        "17.78 cm Smartplay Studio with Smartphone Navigation"
    ]

    print("\n" + "="*70)
    print(" 🚗 SPHERICAL EXTRACTOR: ON-THE-FLY NLP MAPPING SIMULATION ")
    print("="*70)
    
    for raw in raw_pdf_table_cells:
        # Step 1: Extractor hits the raw string and asks the fast O(1) Engine
        canonical_id = OntologyEngine.resolve_feature_id(raw)
        
        # Step 2: Extractor retrieves the category for database insertion
        category = OntologyEngine._attributes.get(canonical_id, {}).get('category', 'uncategorized')
        
        # Determine mapping type for display
        mapping_type = "🎯 CANONICAL HIT" if "ext_unreviewed" not in canonical_id else "⚠️ FALLBACK"
        
        print(f"RAW PDF CELL: '{raw}'")
        print(f"  └─> {mapping_type} -> ID: '{canonical_id}' | Category: '{category}'\n")

if __name__ == "__main__":
    simulate_pdf_extraction()
