# helpers/normalize.py
import pandas as pd
from typing import Dict

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    data = response.get("data", {})
    rows = []
    for shop_id, metrics in data.items():
        row = {"shop_id": int(shop_id)}
        row.update(metrics)
        rows.append(row)
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df  # Al flat
