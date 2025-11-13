# helpers/normalize.py – FINAL & WERKT MET JOUW API
import pandas as pd
from typing import Dict, Any

def extract_latest_data(shop_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract latest day data – safe voor missing keys"""
    dates = shop_data.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0.0, "sales_per_visitor": 0.0}

    # Neem laatste datum
    latest_date = sorted(dates.keys())[-1]
    day_data = dates[latest_date].get("data", {})

    def safe_int(key, default=0):
        val = day_data.get(key)
        try:
            return int(float(val)) if val is not None else default
        except:
            return default

    def safe_float(key, default=0.0):
        val = day_data.get(key)
        try:
            return float(val) if val is not None else default
        except:
            return default

    return {
        "count_in": safe_int("count_in", 0),
        "conversion_rate": safe_float("conversion_rate", 0.0) * 100,  # % weergave
        "turnover": safe_float("turnover", 0.0),
        "sales_per_visitor": safe_float("sales_per_visitor", 0.0)
    }

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    for period, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except:
                continue

            kpi = extract_latest_data(shop_info)
            row = {
                "shop_id": shop_id,
                **kpi
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df  # geen pivot nodig
