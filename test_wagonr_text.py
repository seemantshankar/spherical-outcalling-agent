import pdfplumber

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
pages = list(range(1, 15)) # Assuming it's less than 15 pages

with pdfplumber.open(pdf_path) as pdf:
    for p in pages:
        page = pdf.pages[p-1]
        print(f"--- PAGE {p} TEXT ---")
        text = page.extract_text()
        if text:
            print(text[:1000])
