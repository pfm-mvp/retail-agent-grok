import pandas as pd
from typing import Dict

def extract_latest_date_data(shop_data: Dict) -> Dict:
    dates = shop_data.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0, "sales_per_visitor": 0.0}
    
    latest_date = sorted(dates.keys())[-1]
    date_entry = dates.get(latest_date, {})
    day_data = date_entry.get("data", {})
    
    count_in_str = day_data.get("count_in", "0")
    count_in = int(count_in_str) if count_in_str else 0
    
    return {
        "count_in": count_in,
        "conversion_rate": float(day_data.get("conversion_rate", 0) or 0) * 100,
        "turnover": float(day_data.get("turnover", 0) or 0),
        "sales_per_visitor": float(day_data.get("sales_per_visitor", 0) or 0)
    }

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    data = response.get("data", {})
    rows = []
    for period in data.values():
        for shop_id, shop_info in period.items():
            kpi_data = extract_latest_date_data(shop_info)
            row = {
                "shop_id": int(shop_id),
                **kpi_data  # <--- Gebruik ** om shop_id te behouden
            }
            rows.append(row)
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
