import os
from sqlalchemy import create_engine, text

# Get URL from environment or fallback to localhost
db_url = "postgresql://admin:adminpassword@localhost:5432/oem_rag"
engine = create_engine(db_url)

with engine.connect() as conn:
    res = conn.execute(text("SELECT DISTINCT trim FROM spec_facts"))
    print("ALL TRIMS IN DB:")
    for row in res:
        print(f" - {row[0]}")
    
    res = conn.execute(text("SELECT trim, feature_id, precomputed_value_display FROM spec_facts WHERE trim ILIKE '%ESP%' LIMIT 10"))
    print("\nSAMPLE ESP ROWS:")
    for row in res:
        print(row)
