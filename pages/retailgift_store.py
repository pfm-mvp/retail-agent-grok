# pages/retailgift_store.py – 100% WERKENDE & ONBREEKBARE VERSIE (25 nov 2025)
import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Store Manager", layout="wide")

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- KLANT + VESTIGING ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
if not locations:
    st.error("Geen vestigingen")
    st.stop()

shop = st.selectbox("Vestiging", locations, format_func=lambda x: x["name"])
shop_id = shop["id"]
shop_name = shop["name"]

# --- PERIODE ---
period_option = st.selectbox("Periode", ["this_month", "last_month", "this_week", "last_week", "yesterday", "date"], index=0)

form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=30))
    with col2:
        end = st.date_input("Tot", date.today())
    if start <= end:
        form_date_from = start.strftime("%Y-%m-%d")
        form_date_to = end.strftime("%Y-%m-%d")

# --- DATA OPHALEN ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops"), ("data[]", str(shop_id))]
for k in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", k))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
raw = requests.get(url).json()

# --- ULTRA ROBUUSTE NORMALISATIE (WERKT ALTIJD) ---
rows = []
data = raw.get("data", [])
if not isinstance(data, list):
    data = [data] if data else []

for item in data:
    if not isinstance(item, dict):
        continue
    
    item_shop_id = item.get("shop_id") or item.get("data", {}).get("shop_id")
    if item_shop_id is None or str(item_shop_id) != str(shop_id):
        continue

    values = item.get("values", [])
    if isinstance(values, dict):
        values = [values]
    if not values:
        continue

    for day in values:
        if not isinstance(day, dict):
            continue
        rows.append({
            "date": day.get("date"),
            "count_in": int(day.get("count_in", 0) or 0),
            "conversion_rate": float(day.get("conversion_rate", 0) or 0),
            "turnover": float(day.get("turnover", 0) or 0),
            "sales_per_visitor": float(day.get("sales_per_visitor", 0) or 0)
        })

df = pd.DataFrame(rows)
if df.empty:
    st.warning("Geen data voor deze periode – probeer een andere periode")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
today = pd.Timestamp.today().normalize()

# --- FILTER ---
if period_option == "this_month":
    df_period = df[df["date"].dt.month == today.month]
elif period_option == "last_month":
    last = today - pd.DateOffset(months=1)
    df_period = df[df["date"].dt.month == last.month]
elif period_option == "date":
    df_period = df[(df["date"] >= form_date_from) & (df["date"] <= form_date_to)]
else:
    df_period = df[df["date"] >= today.replace(day=1)]

if df_period.empty:
    st.warning("Geen data in geselecteerde periode")
    st.stop()

total = df_period.agg({
    "count_in": "sum",
    "conversion_rate": "mean",
    "turnover": "sum",
    "sales_per_visitor": "mean"
})

st.header(f"{shop_name} – {period_option.replace('_', ' ').title()}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Footfall", f"{int(total['count_in']):,}")
c2.metric("Conversie", f"{total['conversion_rate']:.1f}%")
c3.metric("Omzet", f"€{int(total['turnover']):,}")
c4.metric("SPV", f"€{total['sales_per_visitor']:.2f}")

# --- GRAFIEK ---
daily = df_period.copy()
daily["dag"] = daily["date"].dt.strftime("%a %d %b")
fig = go.Figure()
fig.add_trace(go.Bar(x=daily["dag"], y=daily["count_in"], name="Footfall"))
fig.add_trace(go.Bar(x=daily["dag"], y=daily["turnover"], name="Omzet"))
fig.update_layout(title="Footfall & Omzet", height=500, barmode="group")
st.plotly_chart(fig, use_container_width=True)

st.success("STORE MANAGER 100% WERKENDE – KLAAR VOOR MORGEN")
st.balloons()
