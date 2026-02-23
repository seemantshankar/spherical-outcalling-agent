import pandas as pd
import numpy as np
import camelot

tables = camelot.read_pdf("/Users/seemantshankar/Downloads/WagonR-Brochure.pdf", pages="3,5,6", flavor='lattice')
for i, t in enumerate(tables):
    if not t.df.empty and len(t.df.columns) > 1:
        data_cols = t.df.iloc[:, 1:]
        data_non_empty1 = data_cols.astype(str).replace('None', '').replace('nan', '').apply(lambda x: x.str.strip() != '').sum().sum()
        data_non_empty2 = data_cols.astype(str).replace(r'^\s*$|^nan$|^None$', '', regex=True).apply(lambda x: x.str.strip() != '').sum().sum()
        print(f"Table {i} data_non_empty1: {data_non_empty1}, data_non_empty2: {data_non_empty2}")

