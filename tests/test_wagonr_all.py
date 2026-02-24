import camelot
import pandas as pd

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
pages = "1-6" # There are 6 pages

tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice')
print(f"Num lattice tables: {tables.n}")
for i, t in enumerate(tables):
    print(f"--- Table {i} on page {t.page} ---")
    df = t.df
    # Print the whole table
    print(df.to_string())
