# helpers/normalize.py – FINAL & 1 ROW PER DAG
import pandas as pd
from typing import Dict, Any

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    for period, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except:
                continue

            dates = shop_info.get("dates", {})
            for date_key, date_data in dates.items():
                day = date_data.get("data", {})
                
                def safe_float(val, default=0.0):
                    try:
                        return float(val) if val is not None else default
                    except:
                        return default

                def safe_int(val, default=0):
                    try:
                        return int(float(val)) if val is not None else default
                    except:
                        return default

                row = {
                    "shop_id": shop_id,
                    "date": date_key,
                    "count_in": safe_int(day.get("count_in")),
                    "conversion_rate": safe_float(day.get("conversion_rate")),
                    "turnover": safe_float(day.get("turnover")),
                    "sales_per_visitor": safe_float(day.get("sales_per_visitor"))
                }
                rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df  # geen pivot nodig
