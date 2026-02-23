import pytest
from src.ontology.engine import OntologyEngine
from src.spherical_retrieval import SphericalRetrievalEngine

def test_ontology_resolution():
    # Test core feature resolution exact match
    assert OntologyEngine.resolve_feature_id("fuel_efficiency") == "fuel_efficiency"
    
    # Test synonym resolution
    assert OntologyEngine.resolve_feature_id("mileage") == "fuel_efficiency"
    assert OntologyEngine.resolve_feature_id("electric windows") == "power_windows"
    
    # Test unreviewed extension
    assert OntologyEngine.resolve_feature_id("Heated Seats") == "ext_unreviewed_heated_seats"

def test_template_rendering():
    # Test numeric format
    output = OntologyEngine.render_template("fuel_efficiency", {"numeric": 24.3, "unit": "kmpl"})
    assert output == "The certified mileage is 24.3 kmpl."
    
    # Test scope format
    output = OntologyEngine.render_template("power_windows", {"scope": "front_and_rear"})
    assert output == "Power windows are front_and_rear."
    
    # Test fallback formatting for unreviewed extensions
    output = OntologyEngine.render_template("ext_unreviewed_heated_seats", {"text": "Yes"})
    assert output == "The value for heated seats is Yes ."

def test_retrieval_query_hashing():
    hash1 = SphericalRetrievalEngine.generate_variant_hash(
        "maruti_suzuki", "wagonr", 2024, "VXi", "K12N", "AMT", "petrol", "IN"
    )
    hash2 = SphericalRetrievalEngine.generate_variant_hash(
        "maruti_suzuki", "wagonr", 2024, "VXi", "K12N", "AMT", "petrol", "IN"
    )
    # Hashing should be deterministic
    assert hash1 == hash2
    
    hash3 = SphericalRetrievalEngine.generate_variant_hash(
        "maruti_suzuki", "wagonr", 2024, "ZXi", "K12N", "AMT", "petrol", "IN"
    )
    # Different trim should yield different hash
    assert hash3 != hash1

def test_get_cross_sell():
    # Test known cross-sell
    cross_sells = SphericalRetrievalEngine._get_cross_sell("maruti_suzuki", "wagonr")
    assert cross_sells is not None
    assert len(cross_sells) == 2
    assert cross_sells[0].model == "ciaz"
    assert cross_sells[0].reason == "more_power"
    assert cross_sells[1].model == "brezza"
    
    # Test unknown
    assert SphericalRetrievalEngine._get_cross_sell("unknown_oem", "model_x") is None
