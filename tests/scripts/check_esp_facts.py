from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()
results = db.query(SpecFact.trim, SpecFact.feature_id, SpecFact.precomputed_value_display)\
            .filter(SpecFact.trim.ilike('%ESP%'))\
            .all()

print(f"Found {len(results)} facts under ESP-related 'trims':")
for r in results[:20]:
    print(r)
