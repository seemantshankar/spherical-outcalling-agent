import fitz
doc = fitz.open("/Users/seemantshankar/Downloads/WagonR-Brochure.pdf")
for i in [2, 4, 5]: # Pages 3, 5, 6 (0-indexed)
    print(f"--- Page {i+1} ---")
    print(doc[i].get_text()[:1000])
