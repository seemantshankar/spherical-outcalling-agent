from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()
trims = db.query(SpecFact.trim).distinct().all()
print("Unique trims in DB:")
for t in trims:
    print(f"'{t[0]}'")

esp_facts = db.query(SpecFact.trim, SpecFact.feature_id, SpecFact.precomputed_value_display)\
              .filter(SpecFact.trim.ilike('%ESP%'))\
              .limit(5).all()
print("\nSample ESP facts:")
for r in esp_facts:
    print(r)
