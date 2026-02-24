from src.ontology.engine import OntologyEngine
import difflib

# Keys that failed to map in the CSV:
failures = [
    "kerb weight (kg)", 
    "maximum torque cng (nm @ rpm)",
    "low fuel warning",
    "seating capacity",
    "transmission",
    "tyre size",
    "tyre type",
    "wheelbase (mm)",
    "width (mm)"
]

print("Synonym map keys:", list(OntologyEngine._synonym_map.keys())[:10])

for f in failures:
    # What does get_close_matches suggest?
    matches = difflib.get_close_matches(f, OntologyEngine._synonym_map.keys(), n=1, cutoff=0.8)
    
    # What does it map to?
    mapped_id = OntologyEngine._synonym_map[matches[0]] if matches else None
    print(f"FAILED RAW: '{f}' -> FUZZY MAPS TO -> {matches[0] if matches else 'NONE'} -> ID: {mapped_id}")
