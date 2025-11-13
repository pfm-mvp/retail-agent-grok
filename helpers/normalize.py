# helpers/normalize.py – FINAL & ALLE DAGEN + DATE KOLOM
import pandas as pd
from typing import Dict, Any

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    # Loop over period (bijv. "this_week")
    for period_key, shops in data.items():
        # Loop over shops (bijv. "29641")
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except (ValueError, TypeError):
                continue

            # GET DATES DICT
            dates_dict = shop_info.get("dates", {})
            if not isinstance(dates_dict, dict):
                continue

            # LOOP OVER ELKE DAG
            for date_label, date_entry in dates_dict.items():
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}

                # SAFE PARSING
                def safe_float(val, default=0.0):
                    try:
                        return float(val) if val is not None else default
                    except (ValueError, TypeError):
                        return default

                def safe_int(val, default=0):
                    try:
                        return int(float(val)) if val is not None else default
                    except (ValueError, TypeError):
                        return default

                row = {
                    "shop_id": shop_id,
                    "date": date_label.strip(),  # <-- CLEAN DATE LABEL
                    "count_in": safe_int(day_data.get("count_in")),
                    "conversion_rate": safe_float(day_data.get("conversion_rate")),
                    "turnover": safe_float(day_data.get("turnover")),
                    "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
                }
                rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df  # Geen pivot nodig
