from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()
results = db.query(SpecFact.trim, SpecFact.engine_code, SpecFact.fuel_type)\
            .filter(SpecFact.fuel_type == 'CNG')\
            .distinct().all()

print("CNG Variants in DB:")
for r in results:
    print(r)
