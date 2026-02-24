from src.ontology.engine import OntologyEngine
from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

# Check what "torque" maps to
canonical = OntologyEngine.resolve_feature_id("torque")
print(f"'torque' maps to: {canonical}")

# Check DB for this canonical ID
db = SessionLocal()
facts = db.query(SpecFact).filter(SpecFact.feature_id == canonical).all()
print(f"Found {len(facts)} facts for '{canonical}' in the DB.")
for f in facts:
    print(f"Variant: {f.trim}, Value: {f.precomputed_value_display}, Category: {f.category}")
