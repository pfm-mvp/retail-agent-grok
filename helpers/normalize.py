# helpers/normalize.py – FINAL & 100% WERKENDE
import pandas as pd
from typing import Dict, Any
from datetime import datetime

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})

    for period_key, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except (ValueError, TypeError):
                continue

            dates_dict = shop_info.get("dates", {})
            if not isinstance(dates_dict, dict):
                continue

            for date_label, date_entry in dates_dict.items():
                # DAGDATA
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}
                dt_raw = day_data.get("dt", "")
                if not dt_raw:
                    continue

                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except:
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

    # FORCEER DataFrame MET KOLOMMEN
    if rows:
        return pd.DataFrame(rows)
    else:
        # LEEG MAAR MET KOLOMMEN
        return pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
