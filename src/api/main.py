# pyre-ignore-all-errors
from fastapi import FastAPI
from src.api.router import router as retrieval_router
from src.storage.database import init_db

app = FastAPI(
    title="OEM RAG Voice Agent Backend",
    description="Phase 1: Extraction & Retrieval modules for automotive specs.",
    version="1.0.0"
)

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# In a real production setup, we'd use Alembic for migrations instead of create_all
@app.on_event("startup")
def on_startup():
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Warning: Could not initialize database. Is Postgres running? Error: {e}")

app.include_router(retrieval_router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "oem_rag_backend"}
