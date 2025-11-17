# helpers/normalize.py – FINAL & 100% WERKENDE VERSIE
import pandas as pd
from datetime import datetime
from typing import Dict, Any

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})

    # ALLEEN VOOR DEBUG – ZET OP False IN PRODUCTIE
    HARD_TEST = False
    if HARD_TEST:
        return pd.DataFrame([
            {"shop_id": 29641, "date": "2025-11-10", "count_in": 264, "conversion_rate": 14.39, "turnover": 654.44, "sales_per_visitor": 2.48},
            {"shop_id": 29641, "date": "2025-11-11", "count_in": 426, "conversion_rate": 16.2,  "turnover": 1325.32, "sales_per_visitor": 3.11},
            {"shop_id": 29641, "date": "2025-11-12", "count_in": 168, "conversion_rate": 13.1,  "turnover": 409.74,  "sales_per_visitor": 2.44},
            {"shop_id": 29641, "date": "2025-11-13", "count_in": 48,  "conversion_rate": 0.0,   "turnover": 0.0,     "sales_per_visitor": 0.0},
            {"shop_id": 29641, "date": "2025-11-14", "count_in": 203, "conversion_rate": 0.0,   "turnover": 0.0,     "sales_per_visitor": 0.0},
        ])

    for period_key, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except:
                continue

            dates_dict = shop_info.get("dates", {})
            if not isinstance(dates_dict, dict):
                continue

            for date_label, date_entry in dates_dict.items():
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}

                dt_raw = day_data.get("dt", "")
                if not dt_raw:
                    continue

                try:
                    # Gebruik ISO direct → altijd werkend
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_iso = dt_obj.strftime("%Y-%m-%d")  # ← DIT IS CRUCIAAL
                except:
                    continue  # Skip ongeldige datum

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
                    "date": date_iso,  # ← ISO string: 2025-11-14 → pd.to_datetime() werkt 100%
                    "count_in": safe_int(day_data.get("count_in")),
                    "conversion_rate": safe_float(day_data.get("conversion_rate")),
                    "turnover": safe_float(day_data.get("turnover")),
                    "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
                }
                rows.append(row)

    df = pd.DataFrame(rows)
    return df if not df.empty else pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
