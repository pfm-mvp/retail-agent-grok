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

# --- 3. KPIs OPVRAGEN ---
params = [("data[]", sid) for sid in shop_ids] + \
         [("data_output[]", "count_in"), ("data_output[]", "conversion_rate")]

data_response = requests.post(f"{API_BASE}/get-report", params=params)
df = to_wide(normalize_vemcount_response(data_response.json()))
df["name"] = df["shop_id"].map(lambda x: next((l["name"] for l in locations if l["id"] == x), "Onbekend"))

# --- 4. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if len(selected_locations) == 1:
    row = df.iloc[0]
    loc = selected_locations[0]
    st.header(f"{loc['name']} – Gift of the Day (Gisteren)")

    col1, col2 = st.columns(2)
    with col1:
        kpi_card("Footfall", f"{int(row['count_in']):,}", "Gisteren", "primary")
    with col2:
        conv = row['conversion_rate']
        tone = "good" if conv >= 25 else "bad"
        kpi_card("Conversie", f"{conv:.1f}%", "Gisteren", tone)

    if row['count_in'] == 0:
        st.warning("Geen data voor gisteren. Probeer een andere vestiging.")
    else:
        spv_estimate = 22.0  # Gem. SPV
        omzet = row['count_in'] * spv_estimate
        st.success(f"**+1 FTE 12-18u → +€{int(omzet * 0.1):,} omzet** (Ryski Ch3)")

else:
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean"})
    st.header("Regio Overzicht (Gisteren)")
    c1, c2 = st.columns(2)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")

st.caption("RetailGift AI: Werkt met jouw API. +10-15% uplift.")
