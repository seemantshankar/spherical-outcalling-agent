import camelot
import pandas as pd
tables = camelot.read_pdf("/Users/seemantshankar/Downloads/WagonR-Brochure.pdf", pages="3,5,6", flavor='lattice')
for i, t in enumerate(tables):
    clean_df = t.df.replace(r'^\s*$', pd.NA, regex=True).replace('nan', pd.NA)
    non_empty1 = clean_df.notna().sum().sum()
    non_empty2 = t.df.astype(str).apply(lambda x: x.str.strip() != '').sum().sum()
    non_empty3 = t.df.astype(str).apply(lambda x: (~x.str.contains(r'^\s*$|^nan$|^None$', case=False, regex=True))).sum().sum()
    print(f"Table {i} shape: {t.df.shape}, non_empty1: {non_empty1}, non_empty2: {non_empty2}, non_empty3: {non_empty3}")
    if non_empty2 > 0:
        print(t.df.head(2))
