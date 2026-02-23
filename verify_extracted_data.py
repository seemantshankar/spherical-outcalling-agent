import sys
import pandas as pd
from src.spherical_extract.ingestion.extractor import process_brochure

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"

print("Running extraction pipeline...")
try:
    facts = process_brochure(
        filepath=pdf_path,
        oem_id="maruti_suzuki",
        campaign_id="c1",
        model_code="wagonr",
        model_year=2024,
        region="IN",
        engine_code="K12N",
        transmission="AMT",
        fuel_type="petrol",
        doc_type="brochure"
    )
    
    print(f"\nSuccessfully extracted {len(facts)} facts.")
    
    # Convert to a DataFrame for easy viewing
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
    
    # Save to CSV
    csv_path = "wagonr_extracted_facts.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved all facts to {csv_path}")
    
    # Save to Markdown for quick reading in IDE
    md_path = "wagonr_extracted_facts.md"
    with open(md_path, "w") as f:
        f.write("# Extracted WagonR Facts\n\n")
        f.write(str(df.to_markdown(index=False)))
    print(f"Saved markdown table to {md_path}")
    
except Exception as e:
    print(f"Extraction failed: {e}")
