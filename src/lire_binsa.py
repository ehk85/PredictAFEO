"""Module de lecture des exports Binsa (format XML Spreadsheet 2003)."""
import re
import pandas as pd
from lxml import etree

SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def lire_binsa(path):
    """Lit un export Binsa (.xls XML) et renvoie un DataFrame."""
    raw = open(path, "rb").read().decode("utf-8")
    raw = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", raw)
    root = etree.fromstring(raw.encode("utf-8"))
    table = root.find(f".//{SS}Worksheet").find(f"{SS}Table")
    rows = []
    for row in table.findall(f"{SS}Row"):
        cells, ci = [], 0
        for cell in row.findall(f"{SS}Cell"):
            idx = cell.get(f"{SS}Index")
            if idx:
                ci = int(idx) - 1
            data = cell.find(f"{SS}Data")
            while len(cells) < ci:
                cells.append(None)
            cells.append(data.text if data is not None else None)
            ci += 1
        rows.append(cells)
    header = rows[1]
    data = [r for r in rows[2:] if any(c is not None for c in r)]
    data = [r + [None] * (len(header) - len(r)) if len(r) < len(header) else r[:len(header)]
            for r in data]
    return pd.DataFrame(data, columns=header)


def noms_uniques(df):
    """Rend uniques les noms de colonnes dupliques (deux colonnes 'Type')."""
    cols = pd.Series(df.columns)
    for d in cols[cols.duplicated()].unique():
        for i, x in enumerate(cols[cols == d].index):
            if i:
                cols[x] = f"{d}_{i}"
    df.columns = cols
    return df
