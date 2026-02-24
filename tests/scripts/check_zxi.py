from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()
facts = db.query(SpecFact.trim, SpecFact.feature_id, SpecFact.precomputed_value_display).filter(SpecFact.trim == 'ZXi+').all()
print(f"Found {len(facts)} facts for ZXi+.")
if facts:
    for f in facts[:10]:
        print(f"Feature: {f.feature_id}, Value: {f.precomputed_value_display}")

# Also check trims available
trims = db.query(SpecFact.trim).distinct().all()
print("All trims in DB:", [t[0] for t in trims])
