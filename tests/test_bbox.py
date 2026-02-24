import pdfplumber

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
page_num = 5

print("\n--- pdfplumber Bounding Boxes ---")
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[page_num - 1]
    
    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }
    bboxes = page.find_tables(table_settings)
    for i, t in enumerate(bboxes):
        print(f"plumber lines Table {i}: bbox {t.bbox}")
        
    table_settings_explicit = {
        "vertical_strategy": "explicit",
        "horizontal_strategy": "explicit",
        "explicit_vertical_lines": page.curves + page.edges,
        "explicit_horizontal_lines": page.curves + page.edges,
    }
    try:
        bboxes_explicit = page.find_tables(table_settings_explicit)
        for i, t in enumerate(bboxes_explicit):
            print(f"plumber explicit Table {i}: bbox {t.bbox}")
    except Exception as e:
        print(f"Explicit lines failed: {e}")
