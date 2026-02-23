import pytest
from unittest.mock import patch, MagicMock
from src.spherical_extract.ingestion.extractor import classify_pdf_pages, process_brochure, SOURCE_PRECEDENCE
from src.storage.schema import SpecFact, AvailabilityState
from src.ontology.engine import OntologyEngine
import pandas as pd

class DummyTable:
    def __init__(self, df, page):
        self.df = df
        self.page = page

def test_source_precedence():
    assert SOURCE_PRECEDENCE["spec_sheet"] == 1
    assert SOURCE_PRECEDENCE["brochure"] == 2

@patch("src.spherical_extract.ingestion.extractor.classify_pdf_pages")
@patch("src.spherical_extract.ingestion.extractor.parse_tables_from_pdf")
def test_process_brochure(mock_parse, mock_classify):
    mock_classify.return_value = [1]
    
    # Create a dummy table mimicking the WagonR Page 5 Spec Matrix
    df = pd.DataFrame({
        0: ["FEATURES", "electric windows", "Fuel Efficiency", "Unknown Feature"],
        1: ["LXi", "-", "24.3 kmpl", "X"],
        2: ["VXi", "O", "24.3 kmpl", "X"],
        3: ["ZXi", "Standard", "24.3 kmpl", "X"]
    })
    mock_parse.return_value = [DummyTable(df, page=1)]
    
    facts = process_brochure(
        filepath="dummy.pdf",
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
    
    # 3 features * 3 trims (variants) = 9 facts
    assert len(facts) == 9
    assert isinstance(facts[0], SpecFact)
    
    # Check if Power Windows are correctly mapped
    power_windows_vxi = next(f for f in facts if f.feature_id == "power_windows" and f.trim == "VXi")
    assert power_windows_vxi.availability_state == AvailabilityState.optional
    
    # Check if a non-available string correctly maps to not_available
    power_windows_lxi = next(f for f in facts if f.feature_id == "power_windows" and f.trim == "LXi")
    assert power_windows_lxi.availability_state == AvailabilityState.not_available
    
    # Check if a standard string correctly maps to standard
    power_windows_zxi = next(f for f in facts if f.feature_id == "power_windows" and f.trim == "ZXi")
    assert power_windows_zxi.availability_state == AvailabilityState.standard
