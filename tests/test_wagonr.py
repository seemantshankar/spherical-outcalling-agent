import camelot
import pandas as pd

pdf_path = "/Users/seemantshankar/Downloads/WagonR-Brochure.pdf"
pages = "3,5,6"

tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice')
print(f"Num lattice tables: {tables.n}")
for t in tables:
    clean_df = t.df.replace(r'^\s*$', pd.NA, regex=True).replace('nan', pd.NA)
    non_empty = clean_df.notna().sum().sum()
    print(f"Table on page {t.page} has {non_empty} non-empty cells.")
    print("df.head():")
    print(t.df.head())
    print("clean_df.head():")
    print(clean_df.head())
