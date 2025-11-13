# pages/retailgift.py – FINAL & WERKT ZONDER CBS/WEER
import streamlit as st
import requests
import pandas as pd
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 1. KLANTEN ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Kies klant", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

if not client_id:
    st.error("Geen klant geselecteerd.")
    st.stop()

# --- 2. LOCATIES ---
try:
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
except:
    st.error("Kon locaties niet ophalen.")
    st.stop()

selected = st.multiselect(
    "Vestiging(en)", locations,
    format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 3. PERIODE ---
period = st.selectbox("Periode", ["yesterday", "today", "this_week"], index=0)

# --- 4. KPIs OPVRAGEN ---
params = [
    ("period", period),
    ("step", "day")
]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

query_string = urlencode(params, doseq=True, safe='[]')
data_response = requests.get(f"{API_BASE}/get-report?{query_string}")
raw_json = data_response.json()

# --- DEBUG ---
st.subheader("DEBUG: API URL")
st.code(data_response.url, language="text")
st.subheader("DEBUG: Raw Response")
st.json(raw_json, expanded=False)

# --- 5. NORMALISEER ---
df = to_wide(normalize_vemcount_response(raw_json))

if df.empty:
    st.error(f"Geen data voor {period}. Probeer 'today'.")
    st.stop()

location_map = {loc["id"]: loc.get("name", "Onbekend") for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. ROL ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"], index=0)

# --- 7. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client.get('name', 'Onbekende Klant')}** – *Mark Ryski*")

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – Gift of the Day ({period})")
    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", period, "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "target >25%", "good" if row['conversion_rate'] >= 25 else "bad")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", period, "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", period, "neutral")

    st.success("**Actie:** +2 FTE piekuren → +5-10% conversie (Ryski Ch3)")

elif role == "Regio Manager":
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Regio Overzicht ({period})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))

else:  # Directie
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Keten Overzicht ({period})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

st.caption("RetailGift AI: 100% LIVE. Vemcount → actie → omzet.")
