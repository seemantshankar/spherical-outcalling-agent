from pydantic import BaseModel
from typing import Optional

class ExtractedVariantFact(BaseModel):
    feature_name: str
    variant_name: str
    raw_value: str
    page_number: int
    source_priority: int
    confidence_score: float
