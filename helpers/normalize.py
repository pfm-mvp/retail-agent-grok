# helpers/normalize.py – FINAL & SAFE PARSING
import pandas as pd
from typing import Dict

def extract_latest_date_data(shop_info: Dict) -> Dict:
    dates = shop_info.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0.0, "sales_per_visitor": 0.0}
    
    latest = sorted(dates.keys())[-1]
    day_data = dates[latest].get("data", {})

    def safe_float(key, default=0.0):
        val = day_data.get(key)
        try:
            return float(val) if val is not None else default
        except:
            return default

    return {
        "count_in": int(safe_float("count_in", 0)),
        "conversion_rate": safe_float("conversion_rate", 0.0),  # GEEN *100
        "turnover": safe_float("turnover", 0.0),
        "sales_per_visitor": safe_float("sales_per_visitor", 0.0)
    }

    # --- SAFE FLOATS ---
    def safe_float(key, default=0.0):
        val = day_data.get(key, default)
        try:
            return float(val or default)
        except (ValueError, TypeError):
            return default

    return {
        "count_in": count_in,
        "conversion_rate": safe_float("conversion_rate", 0.0) * 100,
        "turnover": safe_float("turnover", 0.0),
        "sales_per_visitor": safe_float("sales_per_visitor", 0.0)
    }

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    data = response.get("data", {})
    rows = []
    
    for period, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            shop_id = int(shop_id_str)
            kpi_data = extract_latest_date_data(shop_info)
            row = {
                "shop_id": shop_id,
                **kpi_data
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df  # nog geen pivot nodig
