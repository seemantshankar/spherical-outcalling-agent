from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

db = SessionLocal()
facts = db.query(SpecFact.feature_id, SpecFact.precomputed_value_display)\
          .filter(SpecFact.trim == 'VXi', SpecFact.engine_code == 'K10C', SpecFact.fuel_type == 'CNG', SpecFact.feature_id.like('%capacity%'))\
          .all()

for f in facts:
    print(f"Feature: {f.feature_id}, Value: {f.precomputed_value_display}")
