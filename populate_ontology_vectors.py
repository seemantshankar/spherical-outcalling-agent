import os
import yaml
import sys
from openai import OpenAI
from sqlalchemy import text

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from storage.database import SessionLocal, engine
from storage.schema import OntologyFeatureVector, Base

from dotenv import load_dotenv
load_dotenv()

def populate_vectors():
    # Ensure vector extension is enabled before creating tables
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        
    Base.metadata.create_all(bind=engine)
    
    yaml_path = os.path.join(os.path.dirname(__file__), "src", "ontology", "vehicle_ontology.yaml")
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
        
    features = data.get("attributes", {})
    if not features:
        print("No attributes found in ontology.")
        return
        
    api_key = os.environ.get("OPENROUTER_API_KEY")
    embedding_model = os.environ.get("EMBEDDINGS_LLM", "openai/text-embedding-3-small")
    
    print(f"Using Embedding Model: {embedding_model}")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    db = SessionLocal()
    try:
        count = 0
        for feat_id, feat_data in features.items():
            category = feat_data.get("category", "uncategorized")
            synonyms = feat_data.get("synonyms", [])
            template = feat_data.get("template", "")
            
            # Combine into a rich semantic string
            semantic_string = f"Feature: {feat_id}\nCategory: {category}\nSynonyms: {', '.join(synonyms)}\nDescription: {template}"
            
            # Embed
            try:
                res = client.embeddings.create(input=[semantic_string], model=embedding_model)
                embedding = res.data[0].embedding
                
                # Check if exists
                existing = db.query(OntologyFeatureVector).filter_by(canonical_id=feat_id).first()
                if existing:
                    existing.category = category
                    existing.description = semantic_string
                    existing.embedding = embedding
                else:
                    new_vec = OntologyFeatureVector(
                        canonical_id=feat_id,
                        category=category,
                        description=semantic_string,
                        embedding=embedding
                    )
                    db.add(new_vec)
                count += 1
                if count % 20 == 0:
                    print(f"Embedded {count} features...")
            except Exception as e:
                print(f"Failed to embed {feat_id}: {e}")
                
        db.commit()
        print(f"Successfully populated {count} feature embeddings.")
        
    finally:
        db.close()

if __name__ == "__main__":
    populate_vectors()
