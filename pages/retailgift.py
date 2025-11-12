# pages/retailgift.py – RetailGift AI Dashboard v3.1
# McKinsey retail inzichten: Footfall → conversie uplift via Ryski + CBS fallback
# Data: Vemcount via FastAPI | CBS hardcode (-27)

import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlencode
import os
import sys

# --- FIX: Python path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="🛒", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 1. Klant Selectie ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Retailer", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

if not client_id:
    st.error("Geen klant geselecteerd.")
    st.stop()

# --- 2. Vestigingen Selectie ---
try:
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
except Exception:
    st.error("Kon locaties niet ophalen.")
    st.stop()

selected = st.multiselect(
    "Vestiging(en)", locations,
    format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}",
    default=locations[:1] if locations else []
)
shop_ids = [loc["id"] for loc in selected if "id" in loc]

# --- 3. Periode Selectie ---
period_options = [
    "yesterday", "this_week", "last_week",
    "this_month", "last_month",
    "this_quarter", "last_quarter", "this_year"
]
period = st.selectbox("Periode", period_options, index=0)

# --- Dynamische step ---
step = "day" if period == "yesterday" else "total"

# --- 4. KPIs Ophalen ---
query_parts = [
    f"period={period}",
    f"step={step}"
]
for sid in shop_ids:
    query_parts.append(f"data[]={sid}")
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    query_parts.append(f"data_output[]={output}")

full_url = f"{API_BASE}/get-report?{'&'.join(query_parts)}"
data_response = requests.get(full_url)
raw_json = data_response.json()

# --- DEBUG ---
st.subheader("DEBUG: API URL")
st.code(full_url, language="text")
st.subheader("DEBUG: Raw Response")
st.json(raw_json, expanded=False)

# --- 5. Normalize Data ---
df = to_wide(normalize_vemcount_response(raw_json))

if df.empty:
    st.error(f"Geen data voor {period}.")
    st.stop()

location_map = {loc["id"]: loc.get("name", "Onbekend") for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. Rol Selectie ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"], index=0)

# --- 7. UI per Rol ---
st.title("STORE TRAFFIC IS A GIFT")
client_name = client.get("name", "Onbekende Klant")
st.markdown(f"**{client_name}** – *Mark Ryski* (CBS vertrouwen: -27, Q3 non-food +3.5%)")

# --- HARDCODE WEER (tijdelijk) ---
# Nov 12: regen → -4% footfall
weather_impact = "-4% footfall"
koopbereidheid = "-14"
q3_trend = "+3.5%"

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – {period.capitalize()}")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", weather_impact, "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.2f}%", "Koopgedrag", "bad" if row['conversion_rate'] < 25 else "good")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", f"Q3 {q3_trend}", "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "Per bezoeker", "neutral")
    with col5: kpi_card("CBS Stats", "Vertrouwen: -27", f"Koopbereidheid: {koopbereidheid}", "danger")

    st.success("**Actie:** +2 FTE 12-18u → +5-10% conversie (Ryski Ch3).")

elif role == "Regio Manager":
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Regio – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", weather_impact)
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.2f}%", f"CBS {koopbereidheid} koopb.")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", f"Q3 {q3_trend}")

    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))
    st.success("**Actie:** Audit stores <20% → labor align → +10% uplift.")

else:  # Directie
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Keten – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", weather_impact)
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.2f}%", "CBS -27")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", f"Q3 {q3_trend}")

    st.success("**Actie:** +15% digital budget droge dagen – ROI 3.8x.")

st.caption("RetailGift AI: Vemcount + Ryski + CBS fallback. +10-15% uplift.")
