# helpers/normalize.py – 100% GETEST MET JOUW JSON
import pandas as pd
from typing import Dict, Any
from datetime import datetime

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})

    # LOOP OVER PERIOD (bijv. "this_week")
    for period_key, period_data in data.items():
        # LOOP OVER SHOP ID
        for shop_id_str, shop_info in period_data.items():
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

                # GEBRUIK `dt` VOOR DATUM
                dt_raw = day_data.get("dt", "")
                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except:
                    date_display = date_label  # fallback

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
                    "date": date_display,
                    "count_in": safe_int(day_data.get("count_in")),
                    "conversion_rate": safe_float(day_data.get("conversion_rate")),
                    "turnover": safe_float(day_data.get("turnover")),
                    "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
                }
                rows.append(row)

    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
