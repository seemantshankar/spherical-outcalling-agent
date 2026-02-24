import sys, os
# Directly import without triggering src/__init__.py
from src.ontology.engine import OntologyEngine

print("Test 1:", OntologyEngine.resolve_feature_id('River Crossing'))
print("Test 2:", OntologyEngine.resolve_feature_id('milage'))
print("Test 3:", OntologyEngine.resolve_feature_id('Unknown Test'))
