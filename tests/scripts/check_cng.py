from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()

# 1. Fetch facts matching this config
facts = db.query(SpecFact.trim, SpecFact.engine_code, SpecFact.transmission, SpecFact.fuel_type, SpecFact.feature_id, SpecFact.precomputed_value_display)\
          .filter(SpecFact.trim == 'VXi', SpecFact.transmission == 'MT', SpecFact.fuel_type == 'CNG', SpecFact.feature_id.like('%fuel%tank%cap%'))\
          .all()
          
print(f"Found {len(facts)} fuel tank facts for VXi MT CNG")
for f in facts:
    print(f"Feature: {f.feature_id}, Value: {f.precomputed_value_display}")

# 2. See what fuel types actually exist for VXi MT
all_vxi = db.query(SpecFact.trim, SpecFact.engine_code, SpecFact.transmission, SpecFact.fuel_type)\
            .filter(SpecFact.trim == 'VXi', SpecFact.transmission == 'MT')\
            .distinct().all()

print("\nAvailable VXi MT configurations in DB:")
for v in all_vxi:
    print(v)
