# helpers/normalize.py – FINAL & GEBRUIK dt ALS date
import pandas as pd
from typing import Dict, Any

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    # Loop over period (bijv. "this_week")
    for period_key, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except (ValueError, TypeError):
                continue

            # DIRECTE DAGDATA (geen "dates" dict)
            day_data = shop_info.get("data", {})
            if not isinstance(day_data, dict):
                continue

            dt_raw = day_data.get("dt", "")
            if not dt_raw:
                continue

            # Format: "2025-11-13 00:00:00" → "Wed. Nov 12, 2025" (of hou als ISO)
            try:
                from datetime import datetime
                dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                date_label = dt_obj.strftime("%a. %b %d, %Y")  # Mon. Nov 10, 2025
            except:
                date_label = dt_raw.split(" ")[0]  # fallback: 2025-11-13

            # SAFE PARSING
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
                "date": date_label,  # <-- VAN dt
                "count_in": safe_int(day_data.get("count_in")),
                "conversion_rate": safe_float(day_data.get("conversion_rate")),
                "turnover": safe_float(day_data.get("turnover")),
                "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
