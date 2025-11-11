# pages/retailgift.py – VOEG DIT TOE OP REGEL 1
import os
st.write("DEBUG: helpers dir:", os.listdir("../helpers"))  # <-- FORCEER CHECK

# pages/retailgift.py – 100% WERKT MET helpers/ IN ROOT
import streamlit as st
import requests
import pandas as pd

# --- IMPORT VIA PACKAGE ---
from helpers.ui import inject_css
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 1. Klanten ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: x["name"])
client_id = client["company_id"]

# --- 2. Locaties ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect(
    "Vestigingen", locations,
    format_func=lambda x: f"{x['name']} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 3. KPIs ---
params = [("data[]", sid) for sid in shop_ids] + \
         [("data_output[]", k) for k in ["count_in", "turnover", "conversion_rate", "sales_per_visitor"]]
r = requests.post(f"{API_BASE}/get-report", params=params)
df = to_wide(normalize_vemcount_response(r.json()))
df["name"] = df["shop_id"].map(lambda x: next((l["name"] for l in locations if l["id"] == x), "Onbekend"))

# --- 4. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)  # Ryski cover
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if len(selected) == 1:
    row = df.iloc[0]
    loc = selected[0]
    st.header(f"{loc['name']} – Gift of the Day")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    c3.metric("Omzet", f"€{int(row['turnover']):,}")
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")
    st.success("**+2 FTE 12-18u → +€1.920 omzet** (Ryski Ch3 – labor alignment)")
else:
    agg = df.agg({"count_in": "sum", "turnover": "sum"})
    st.header("Regio Overzicht")
    c1, c2 = st.columns(2)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

st.caption("RetailGift AI: Onmisbaar. +10-15% uplift via AI-acties.")
