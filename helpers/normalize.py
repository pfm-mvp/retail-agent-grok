# helpers/normalize.py
import pandas as pd
import streamlit as st

def to_wide(data):
    # DEBUG: toon input
    st.sidebar.write("**to_wide() input:**")
    st.sidebar.code(str(data)[:500], language="json")

    if not isinstance(data, dict):
        st.sidebar.error("to_wide: input is geen dict")
        return pd.DataFrame()

    if "data" not in data:
        st.sidebar.error("to_wide: 'data' key ontbreekt")
        return pd.DataFrame()

    if not data["data"]:
        st.sidebar.warning("to_wide: 'data' is leeg → lege DataFrame")
        return pd.DataFrame()

    records = []
    for period_key, shops in data["data"].items():
        if not isinstance(shops, dict):
            continue
        for shop_id, shop_data in shops.items():
            if not isinstance(shop_data, dict):
                continue
            shop_info = shop_data.get("data", {})
            dates = shop_data.get("dates", {})
            if not isinstance(dates, dict):
                continue
            for date_key, date_data in dates.items():
                if not isinstance(date_data, dict):
                    continue
                row = {
                    "shop_id": shop_id,
                    "period": period_key,
                    "date": date_key,
                    **shop_info,
                    **date_data.get("data", {})
                }
                records.append(row)

    df = pd.DataFrame(records)
    st.sidebar.write(f"**to_wide() → {len(df)} rijen**")

    if df.empty:
        return df

    # --- TOTAL RIJ ---
    fixed_periods = ["last_month", "this_month", "last_week", "this_week", "last_quarter", "this_quarter", "last_year", "this_year"]
    if df["period"].iloc[0] in fixed_periods:
        day_df = df[~df["date"].str.contains("total", case=False, na=False)]
        if not day_df.empty:
            total_agg = day_df.agg({
                "count_in": "sum",
                "turnover": "sum",
                "conversion_rate": "mean",
                "sales_per_visitor": "mean"
            }).to_dict()

            total_footfall = total_agg["count_in"]
            total_turnover = total_agg["turnover"]
            if total_footfall > 0:
                total_agg["sales_per_visitor"] = round(total_turnover / total_footfall, 2)

            total_agg.update({
                "shop_id": day_df["shop_id"].iloc[0],
                "period": day_df["period"].iloc[0],
                "date": "total",
                "name": day_df.get("name", shop_id).iloc[0] if "name" in day_df.columns else shop_id
            })

            df = pd.concat([df, pd.DataFrame([total_agg])], ignore_index=True)

    numeric_cols = ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df
