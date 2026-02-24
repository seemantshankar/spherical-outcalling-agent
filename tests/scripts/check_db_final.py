import os
from sqlalchemy import create_engine, text

db_url = "postgresql://admin:adminpassword@localhost:5432/oem_rag"
engine = create_engine(db_url)

with engine.connect() as conn:
    res = conn.execute(text("SELECT count(*) FROM spec_facts"))
    print(f"Total rows: {res.fetchone()[0]}")
    
    res = conn.execute(text("SELECT DISTINCT trim FROM spec_facts"))
    print("ALL TRIMS IN DB:")
    for row in res:
        print(f" - {row[0]}")
    
    res = conn.execute(text("SELECT DISTINCT campaign_id, oem_id, model_code FROM spec_facts"))
    print("\nCAMPAIGNS IN DB:")
    for row in res:
        print(row)
