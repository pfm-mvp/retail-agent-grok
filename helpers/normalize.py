# helpers/normalize.py – 100% GETEST + DEBUG
import pandas as pd
from typing import Dict, Any
from datetime import datetime

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})

    print("DEBUG: data keys:", list(data.keys()))  # <--- DEBUG

    for period_key, shops in data.items():
        print(f"DEBUG: period_key = {period_key}")  # <--- DEBUG

        for shop_id_str, shop_info in shops.items():
            print(f"DEBUG: shop_id_str = {shop_id_str}")  # <--- DEBUG

            try:
                shop_id = int(shop_id_str)
            except (ValueError, TypeError):
                print(f"DEBUG: shop_id_str niet int: {shop_id_str}")
                continue

            dates_dict = shop_info.get("dates", {})
            print(f"DEBUG: dates_dict keys: {list(dates_dict.keys())}")  # <--- DEBUG

            if not isinstance(dates_dict, dict):
                print("DEBUG: dates_dict geen dict")
                continue

            for date_label, date_entry in dates_dict.items():
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}
                dt_raw = day_data.get("dt", "")
                print(f"DEBUG: dt_raw = {dt_raw}")  # <--- DEBUG

                if not dt_raw:
                    continue

                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except Exception as e:
                    print(f"DEBUG: datetime fout: {e}")
                    date_display = date_label

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
                print(f"DEBUG: row toegevoegd: {row}")  # <--- DEBUG

    print(f"DEBUG: totaal rows = {len(rows)}")  # <--- DEBUG

    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
