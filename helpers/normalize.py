import pandas as pd
from typing import Dict

def extract_latest_date_data(shop_info: Dict) -> Dict:
    """Parse geneste dates uit shop_info"""
    dates = shop_info.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0, "sales_per_visitor": 0.0}
    
    latest_date = sorted(dates.keys())[-1]
    date_entry = dates.get(latest_date, {})
    day_data = date_entry.get("data", {})
    
    # String to int/float
    count_in_str = day_data.get("count_in", "0")
    count_in = int(count_in_str) if count_in_str.isdigit() else 0
    
    return {
        "count_in": count_in,
        "conversion_rate": float(day_data.get("conversion_rate", 0) or 0) * 100,
        "turnover": float(day_data.get("turnover", 0) or 0),
        "sales_per_visitor": float(day_data.get("sales_per_visitor", 0) or 0)
    }

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    data = response.get("data", {})
    rows = []
    
    for period, shops in data.items():
        for shop_id_str, shop_info in shops.items():
            shop_id = int(shop_id_str)
            kpi_data = extract_latest_date_data(shop_info)
            row = {
                "shop_id": shop_id,
                **kpi_data
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("Geen data in API response.")
    return df

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
