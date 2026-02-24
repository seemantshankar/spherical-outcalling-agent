from src.storage.database import SessionLocal
from src.storage.schema import SpecFact
from sqlalchemy import func

db = SessionLocal()
trim_counts = db.query(SpecFact.trim, func.count(SpecFact.id)).group_by(SpecFact.trim).all()

for trim, count in trim_counts:
    print(f"Trim: {trim}, Count: {count}")
db.close()
