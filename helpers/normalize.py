# helpers/normalize.py – FINAL & 100% WERKENDE
import pandas as pd
from typing import Dict, Any
from datetime import datetime

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})

    # Loop over period (this_week)
    for period_key, shops in data.items():
        # Loop over shop (29641)
        for shop_id_str, shop_info in shops.items():
            try:
                shop_id = int(shop_id_str)
            except:
                continue

            # Get dates dict
            dates_dict = shop_info.get("dates", {})
            if not isinstance(dates_dict, dict):
                continue

            # Loop over each day
            for date_label, date_entry in dates_dict.items():
                # Get day data
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}
                if not day_data:
                    continue

                dt_raw = day_data.get("dt", "")
                if not dt_raw:
                    continue

                # Parse date
                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except:
                    date_display = date_label

                # Safe conversion
                def safe_float(v, default=0.0):
                    try:
                        return float(v) if v is not None else default
                    except:
                        return default

                def safe_int(v, default=0):
                    try:
                        return int(float(v)) if v is not None else default
                    except:
                        return default

                # Build row
                row = {
                    "shop_id": shop_id,
                    "date": date_display,
                    "count_in": safe_int(day_data.get("count_in")),
                    "conversion_rate": safe_float(day_data.get("conversion_rate")),
                    "turnover": safe_float(day_data.get("turnover")),
                    "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
                }
                rows.append(row)

    # Return DataFrame
    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
