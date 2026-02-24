import sys
import os
import pandas as pd

from src.storage.database import SessionLocal
from src.storage.schema import SpecFact

def export_facts():
    db = SessionLocal()
    try:
        facts = db.query(SpecFact).filter(SpecFact.model_code == "wagonr").all()
        print(f"Found {len(facts)} facts in the database.")
        
        data = []
        for f in facts:
            data.append({
                "Category": f.category,
                "Feature_ID": f.feature_id,
                "Trim": f.trim,
                "Value": f.precomputed_value_display,
                "Availability": f.availability_state.name
            })
            
        df = pd.DataFrame(data)
        
        csv_path = "wagonr_extracted_facts.csv"
        df.to_csv(csv_path, index=False)
        print(f"Saved all facts to {csv_path}")
        
        # Let's also print out the unique categories or features related to instrument cluster
        cluster_facts = db.query(SpecFact.feature_id).filter(SpecFact.feature_id.ilike("%cluster%")).distinct().all()
        print("\nFeatures containing 'cluster':")
        for f in cluster_facts:
            print(f" - {f[0]}")
            
    finally:
        db.close()

if __name__ == "__main__":
    export_facts()
