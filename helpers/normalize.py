# helpers/normalize.py – PARSE GENESTE API
import pandas as pd
from typing import Dict, Any

def extract_latest_date_data(shop_data: Dict) -> Dict:
    """Haal data van laatste datum uit 'dates'"""
    dates = shop_data.get("dates", {})
    if not dates:
        return {"count_in": 0, "conversion_rate": 0.0, "turnover": 0, "sales_per_visitor": 0.0}
    
    # Neem laatste datum (meest recente)
    latest_date = sorted(dates.keys())[-1]
    day_data = dates[latest_date].get("data", {})
    
    return {
        "count_in": int(day_data.get("count_in", 0) or 0),
        "conversion_rate": float(day_data.get("conversion_rate", 0) or 0) * 100,  # % maken
        "turnover": float(day_data.get("turnover", 0) or 0),
        "sales_per_visitor": float(day_data.get("sales_per_visitor", 0) or 0)
    }

def normalize_vemcount_response(response: Dict) -> pd.DataFrame:
    data = response.get("data", {})
    rows = []
    
    # API nest onder "yesterday" of "today"
    for period in data.values():  # yesterday, today, etc.
        for shop_id, shop_info in period.items():
            row = {"shop_id": int(shop_id)}
            row.update(extract_latest_date_data(shop_info))
            rows.append(row)
    
    return pd.DataFrame(rows)

def to_wide(df: pd.DataFrame) -> pd.DataFrame:
    return df
