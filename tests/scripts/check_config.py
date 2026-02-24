from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()

# Group by the 3 configuration variables
configs = db.query(SpecFact.engine_code, SpecFact.transmission, SpecFact.fuel_type)\
          .distinct().all()

print("Available configurations in DB:")
for c in configs:
    print(c)
