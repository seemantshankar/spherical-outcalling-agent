from src.ontology.engine import OntologyEngine

terms = [
    "Instrument cluster",
    "Instrument cluster meter theme",
    "cluster theme",
    "meter color",
    "instrument cluster"
]

for t in terms:
    res = OntologyEngine.resolve_feature_id(t)
    print(f"'{t}' -> '{res}'")
