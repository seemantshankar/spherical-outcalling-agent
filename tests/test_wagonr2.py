import camelot
import pandas as pd

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
pages = "5"

tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice')
t = tables[0]
clean_df = t.df.replace(r'^\s*$', pd.NA, regex=True).replace('nan', pd.NA)

for i in range(len(t.df)):
    for j in range(len(t.df.columns)):
        val = t.df.iloc[i, j]
        if pd.notna(clean_df.iloc[i, j]):
            print(f"Row {i}, Col {j}: {repr(val)}")
