# pages/retailgift.py – FINAL & WERKT
import streamlit as st
import requests
import pandas as pd
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON_URL = st.secrets["clients_json_url"]

# --- 1. KLANTEN ---
clients = requests.get(CLIENTS_JSON_URL).json()
client = st.selectbox("Kies klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

# --- 2. LOCATIES ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected_locations = st.multiselect(
    "Vestiging(en)", locations,
    format_func=lambda x: f"{x['name']} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected_locations]

# --- 3. PERIODE ---
period = st.selectbox("Periode", ["yesterday", "today", "this_week"], index=0)

# --- 4. KPIs OPVRAGEN – MEER METRICS ---
params = [("period", period), ("step", "day")]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

data_response = requests.post(f"{API_BASE}/get-report", params=params)
df = to_wide(normalize_vemcount_response(data_response.json()))

if df.empty:
    st.error(f"Geen data voor {period}. Probeer 'today'.")
    st.stop()

# --- 5. NAME ---
location_map = {loc["id"]: loc["name"] for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if len(selected_locations) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – Gift of the Day ({period})")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Footfall", f"{int(row['count_in']):,}", period, "primary")
    with col2:
        conv = row['conversion_rate']
        tone = "good" if conv >= 25 else "bad"
        kpi_card("Conversie", f"{conv:.1f}%", period, tone)
    with col3:
        omzet = int(row['turnover'] or 0)
        kpi_card("Omzet", f"€{omzet:,}", period, "good")
    with col4:
        spv = row['sales_per_visitor']
        kpi_card("SPV", f"€{spv:.2f}", period, "neutral")

else:
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum", "sales_per_visitor": "mean"})
    st.header(f"Regio Overzicht ({period})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}")

st.caption("RetailGift AI: 100% LIVE. +10-15% uplift.")
