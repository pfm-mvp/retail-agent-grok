# helpers/normalize.py – FINAL & PERIOD-BASED
import pandas as pd
from typing import Dict

def extract_latest_date_data(shop_info: Dict, is_yesterday: bool = False) -> Dict:
    dates = shop_info.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0.0, "sales_per_visitor": 0.0}
    
    latest_date = sorted(dates.keys())[-1]
    date_entry = dates.get(latest_date, {})
    day_data = date_entry.get("data", {})

    def safe_float(key, default=0.0):
        val = day_data.get(key)
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    conv = safe_float("conversion_rate", 0.0)
    # yesterday → API geeft %, anders fractie → *100
    if not is_yesterday and conv <= 1.0:
        conv *= 100

    return {
        "count_in": int(safe_float("count_in", 0)),
        "conversion_rate": round(conv, 2),
        "turnover": safe_float("turnover", 0.0),
        "sales_per_visitor": safe_float("sales_per_visitor", 0.0)
    }

def normalize_vemcount_response(response: Dict, period: str = "yesterday") -> pd.DataFrame:
    is_yesterday = (period == "yesterday")
    data = response.get("data", {})
    rows = []
    
    for period_key, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except:
                continue
            kpi_data = extract_latest_date_data(shop_info, is_yesterday=is_yesterday)
            row = {"shop_id": shop_id, **kpi_data}
            rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
