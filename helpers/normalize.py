# helpers/normalize.py – FINAL & SAFE PARSING
import pandas as pd
from typing import Dict

def extract_latest_date_data(shop_info: Dict) -> Dict:
    """Parse geneste dates uit shop_info – 100% veilig"""
    dates = shop_info.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0.0, "sales_per_visitor": 0.0}
    
    latest_date = sorted(dates.keys())[-1]
    date_entry = dates.get(latest_date, {})
    day_data = date_entry.get("data", {})

    # --- SAFE COUNT_IN ---
    count_in_str = day_data.get("count_in", "0")
    count_in = 0
    if count_in_str:
        try:
            count_in = int(count_in_str)
        except (ValueError, TypeError):
            count_in = 0

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
