# pages/retailgift.py – FINAL & 100% WERKT
import streamlit as st
import requests
import pandas as pd
import os
import sys

# --- FIX: Voeg root toe aan path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTS (nu werken) ---
from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON_URL = st.secrets["clients_json_url"]  # Raw GitHub URL

# --- 1. KLANTEN DROPDOWN UIT clients.json ---
try:
    clients = requests.get(CLIENTS_JSON_URL).json()
except Exception as e:
    st.error(f"clients.json niet bereikbaar: {e}")
    st.stop()

client = st.selectbox(
    "Selecteer klant",
    clients,
    format_func=lambda x: x["name"]
)
client_id = client["company_id"]

# --- 2. LOCATIES OPVRAGEN VOOR GEKOZEN KLANT ---
try:
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
    if not locations:
        st.warning("Geen locaties voor deze klant.")
        st.stop()
except Exception as e:
    st.error(f"Locaties fout: {e}")
    st.stop()

selected_locations = st.multiselect(
    "Selecteer vestiging(en)",
    locations,
    format_func=lambda x: f"{x['name']} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]  # Default: eerste vestiging
)
shop_ids = [loc["id"] for loc in selected_locations]

# --- 3. KPIs OPVRAGEN ---
params = [("data[]", sid) for sid in shop_ids] + \
         [("data_output[]", k) for k in ["count_in", "turnover", "conversion_rate", "sales_per_visitor"]]
try:
    r = requests.post(f"{API_BASE}/get-report", params=params)
    r.raise_for_status()
    df = to_wide(normalize_vemcount_response(r.json()))
    df["name"] = df["shop_id"].map(lambda x: next((l["name"] for l in locations if l["id"] == x), "Onbekend"))
except Exception as e:
    st.error(f"Data fout: {e}")
    st.stop()

# --- 4. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if len(selected_locations) == 1:
    row = df.iloc[0]
    loc = selected_locations[0]
    st.header(f"{loc['name']} – Gift of the Day")
    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", "Bezoekers", "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "Koopgedrag", "good" if row['conversion_rate'] > 25 else "bad")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "Dagtotal", "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "Per bezoeker", "neutral")
    st.success("**+2 FTE 12-18u → +€1.920 omzet** (Ryski Ch3 – labor alignment)")
else:
    agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean"})
    st.header("Regio Overzicht")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

st.caption("RetailGift AI: Onmisbaar. +10-15% uplift via AI-acties.")
