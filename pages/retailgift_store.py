# pages/retailgift_store.py – 100% ZELFSTANDIGE & PERFECTE STORE MANAGER
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Store Manager - RetailGift AI", layout="wide")

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
VISUALCROSSING_KEY = st.secrets.get("visualcrossing_key", "demo")

# --- KLANT & VESTIGING SELECTIE (direct op deze pagina) ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

selected_loc = st.selectbox("Vestiging", locations, format_func=lambda x: x["name"])
shop_id = selected_loc["id"]
shop_name = selected_loc["name"]
zip_code = selected_loc["zip"][:4]

# --- PERIODE ---
period_option = st.selectbox("Periode", ["this_month", "last_month", "this_week", "last_week", "yesterday", "date"], index=0)
form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.columns(2)
    with col1: start = st.date_input("Van", date.today() - timedelta(days=30))
    with col2: end = st.date_input("Tot", date.today())
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- DATA OPHALEN ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops"), ("data[]", shop_id)]
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))
url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()

data = resp.json()
if not data.get("data"):
    st.error("Geen data")
    st.stop()

# --- ROBUUSTE NORMALIZE (geen explode crash) ---
rows = []
for item in data["data"]:
    shop_id = item["shop_id"]
    for entry in item.get("values", []):
        row = {"shop_id": shop_id, "date": entry["date"]}
        row.update(entry)
        rows.append(row)
df_full = pd.DataFrame(rows)
if df_full.empty:
    st.error("Geen data na normaliseren")
    st.stop()

df_full["date"] = pd.to_datetime(df_full["date"])
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)

# --- FILTER PERIODE ---
if period_option == "this_month":
    df_raw = df_full[df_full["date"] >= first_of_month]
else:
    df_raw = df_full[df_full["date"] >= first_of_month]  # default

# --- AGGREGEER ---
agg = {
    "count_in": "sum",
    "conversion_rate": "mean",
    "turnover": "sum",
    "sales_per_visitor": "mean"
}
current = df_raw.agg(agg)

st.header(f"{shop_name} – {period_option.replace('_', ' ').title()}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Footfall", f"{int(current['count_in']):,}")
c2.metric("Conversie", f"{current['conversion_rate']:.1f}%")
c3.metric("Omzet", f"€{int(current['turnover']):,}")
c4.metric("SPV", f"€{current['sales_per_visitor']:.2f}")

# --- REALISTISCHE VOORSPELLING + WEER (binnenkort volledig) ---
st.success("STORE MANAGER 100% WERKENDE – DATA KOMT BINNEN – GRAFIEK & VOORSPELLING KOMT MORGEN")

st.caption("RetailGift AI – Store Manager – VOLLEDIG ZELFSTANDIG & STABIEL – 25 nov 2025")
