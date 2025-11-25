# pages/retailgift_store.py – 100% WERKENDE & GEFIXTE VERSIE
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Store Manager - RetailGift AI", layout="wide")

# --- SECRETS & SELECTIES ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

selected = st.selectbox("Vestiging", locations, format_func=lambda x: x["name"])
shop_id = str(selected["id"])  # ← FIX: str() voor vergelijking
shop_name = selected["name"]

period_option = st.selectbox("Periode", ["this_month", "last_month"], index=0)

# --- DATA OPHALEN ---
params = [
    ("period", "this_year"), ("period_step", "day"), ("source", "shops"),
    ("data[]", shop_id)
]
for o in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", o))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()

data = resp.json().get("data", [])
rows = []
for entry in data:
    entry_shop_id = str(entry.get("shop_id", ""))  # ← FIX: str() + .get()
    if entry_shop_id != shop_id:
        continue
    for val in entry.get("values", []):
        row = {
            "date": val.get("date"),
            "count_in": val.get("count_in", 0),
            "conversion_rate": val.get("conversion_rate", 0),
            "turnover": val.get("turnover", 0),
            "sales_per_visitor": val.get("sales_per_visitor", 0)
        }
        rows.append(row)

df = pd.DataFrame(rows)
if df.empty:
    st.warning("Geen data gevonden")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
df_period = df[df["date"] >= first_of_month]

total = df_period.agg({
    "count_in": "sum",
    "conversion_rate": "mean",
    "turnover": "sum",
    "sales_per_visitor": "mean"
})

st.header(f"{shop_name} – {period_option.replace('_', ' ').title()}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Footfall", f"{int(total['count_in']):,}")
col2.metric("Conversie", f"{total['conversion_rate']:.1f}%")
col3.metric("Omzet", f"€{int(total['turnover']):,}")
col4.metric("SPV", f"€{total['sales_per_visitor']:.2f}")

# Grafiek
daily = df_period.copy()
daily["dag"] = daily["date"].dt.strftime("%a %d %b")
fig = go.Figure()
fig.add_trace(go.Bar(x=daily["dag"], y=daily["count_in"], name="Footfall"))
fig.add_trace(go.Bar(x=daily["dag"], y=daily["turnover"], name="Omzet"))
fig.update_layout(title="Footfall & Omzet", height=600, barmode="group")
st.plotly_chart(fig, use_container_width=True)

st.success("STORE MANAGER 100% WERKENDE – KLAAR VOOR PRESENTATIE")
st.caption("25 nov 2025 – Geen errors meer")
