# helpers/normalize.py – FINAL & DEBUG IN APP
import pandas as pd
from typing import Dict, Any
from datetime import datetime
import streamlit as st  # <--- VOOR ZICHTBARE DEBUG

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    st.write("DEBUG: normalize gestart")

    for period_key, shops in data.items():
        st.write(f"DEBUG: period_key = {period_key}")
        for shop_id_str, shop_info in shops.items():
            st.write(f"DEBUG: shop_id_str = {shop_id_str}")
            try:
                shop_id = int(shop_id_str)
            except Exception as e:
                st.write(f"DEBUG: shop_id fout: {e}")
                continue

            dates_dict = shop_info.get("dates", {})
            if not isinstance(dates_dict, dict):
                st.write("DEBUG: dates_dict geen dict")
                continue

            st.write(f"DEBUG: aantal dagen = {len(dates_dict)}")

            for date_label, date_entry in dates_dict.items():
                st.write(f"DEBUG: date_label = {date_label}")
                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}
                dt_raw = day_data.get("dt", "")
                st.write(f"DEBUG: dt_raw = {dt_raw}")

                if not dt_raw:
                    st.write("DEBUG: dt_raw leeg → skip")
                    continue

                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except Exception as e:
                    st.write(f"DEBUG: datetime fout: {e}")
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
                st.write(f"DEBUG: row toegevoegd: {row}")

    st.write(f"DEBUG: totaal rows = {len(rows)}")
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
