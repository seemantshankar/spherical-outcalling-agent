from src.ontology.engine import OntologyEngine
from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

# 1. See what the semantic vector engine maps "power windows" to
canonical = OntologyEngine.resolve_feature_id("power windows")
print(f"'power windows' maps to: {canonical}")

# 2. Check the database facts mapping under this ID
db = SessionLocal()
facts = db.query(SpecFact.trim, SpecFact.precomputed_value_display, SpecFact.feature_id).filter(
    (SpecFact.feature_id.like('%power%window%')) | 
    (SpecFact.feature_id == canonical)
).order_by(SpecFact.trim).all()

print(f"\nFound {len(facts)} window-related facts in DB:")
for f in facts:
    print(f"Trim: {f.trim} | Feature: {f.feature_id} | Value: {f.precomputed_value_display}")
