# helpers/normalize.py – FINAL & 100% WERKENDE
import pandas as pd
from typing import Dict, Any
from datetime import datetime
import streamlit as st

def normalize_vemcount_response(response: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    data = response.get("data", {})
    
    st.write("DEBUG: normalize gestart")
    st.write(f"DEBUG: data keys = {list(data.keys())}")

    for period_key, shops in data.items():
        st.write(f"DEBUG: period_key = {period_key}")
        for shop_id_str, shop_info in shops.items():
            st.write(f"DEBUG: shop_id_str = {shop_id_str}")
            
            # FORCEER int
            try:
                shop_id = int(shop_id_str)
            except Exception as e:
                st.write(f"DEBUG: shop_id fout: {e} → skip shop")
                continue  # alleen skip bij echte fout

            dates_dict = shop_info.get("dates", {})
            st.write(f"DEBUG: dates_dict type = {type(dates_dict)}")
            st.write(f"DEBUG: dates_dict keys = {list(dates_dict.keys())}")

            if not dates_dict:
                st.write("DEBUG: dates_dict leeg → geen data")
                continue

            for date_label, date_entry in dates_dict.items():
                st.write(f"DEBUG: date_label = {date_label}")
                st.write(f"DEBUG: date_entry type = {type(date_entry)}")

                day_data = date_entry.get("data", {}) if isinstance(date_entry, dict) else {}
                st.write(f"DEBUG: day_data keys = {list(day_data.keys())}")

                dt_raw = day_data.get("dt", "")
                st.write(f"DEBUG: dt_raw = '{dt_raw}'")

                if not dt_raw:
                    st.write("DEBUG: dt_raw leeg → skip dag")
                    continue

                try:
                    dt_obj = datetime.fromisoformat(dt_raw.replace(" ", "T"))
                    date_display = dt_obj.strftime("%a. %b %d, %Y")
                except Exception as e:
                    st.write(f"DEBUG: datetime fout: {e} → gebruik label")
                    date_display = date_label

                # SAFE PARSING
                def safe_float(val, default=0.0):
                    try:
                        return float(val) if val is not None else default
                    except:
                        st.write(f"DEBUG: float fout: {val}")
                        return default

                def safe_int(val, default=0):
                    try:
                        return int(float(val)) if val is not None else default
                    except:
                        st.write(f"DEBUG: int fout: {val}")
                        return default

                count_in_raw = day_data.get("count_in")
                st.write(f"DEBUG: count_in_raw = {count_in_raw} (type: {type(count_in_raw)})")

                row = {
                    "shop_id": shop_id,
                    "date": date_display,
                    "count_in": safe_int(count_in_raw),
                    "conversion_rate": safe_float(day_data.get("conversion_rate")),
                    "turnover": safe_float(day_data.get("turnover")),
                    "sales_per_visitor": safe_float(day_data.get("sales_per_visitor"))
                }
                rows.append(row)
                st.write(f"DEBUG: ROW TOEGEVOEGD: {row}")

    st.write(f"DEBUG: TOTAAL ROWS = {len(rows)}")
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["shop_id", "date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"])
