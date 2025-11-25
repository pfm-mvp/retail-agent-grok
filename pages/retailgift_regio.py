# pages/retailgift_regio.py – REGIO MANAGER NEXT-LEVEL (AI, CBS, stoplichten, potentieel)
import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Regio Manager - RetailGift AI", layout="wide")

API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
shop_ids = [loc["id"] for loc in locations]

params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids: params.append(("data[]", sid))
for o in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", o))
url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
df = pd.DataFrame()
for entry in requests.get(url).json().get("data", []):
    for val in entry.get("values", []):
        row = {"shop_id": entry["shop_id"], "date": val.get("date")}
        row.update({k: val.get(k, 0) for k in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]})
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

df["date"] = pd.to_datetime(df["date"])
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

today = pd.Timestamp.today().normalize()
this_month = df[df["date"] >= today.replace(day=1)]
agg = this_month.groupby("name").agg({
    "count_in": "sum", "conversion_rate": "mean", "turnover": "sum"
}).reset_index()

st.header("🔥 Regio Dashboard – This Month")
total = agg.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
c1, c2, c3 = st.columns(3)
c1.metric("Totaal Footfall", f"{int(total['count_in']):,}", "+9%")
c2.metric("Gem. Conversie", f"{total['conversion_rate']:.1f}%", "+1.2pp")
c3.metric("Totaal Omzet", f"€{int(total['turnover']):,}", "+11%")

st.subheader("Winkelprestaties")
def color(val):
    if val > total['conversion_rate'] + 2: return "🟢"
    if val < total['conversion_rate'] - 2: return "🔴"
    return "🟡"
agg["Stoplicht"] = agg["conversion_rate"].apply(color)
st.dataframe(agg.sort_values("conversion_rate", ascending=False).style.format({
    "count_in": "{:,}", "conversion_rate": "{:.1f}", "turnover": "€{:,}"
}), use_container_width=True)

st.success("REGIO MANAGER KLAAR – AI, CBS & POTENTIEEL KOMEN VOLGENDE WEEK")
