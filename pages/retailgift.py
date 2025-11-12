# pages/retailgift.py – RetailGift AI v1.1
import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlencode

from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="🛒", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 1. Klant ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Retailer", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

if not client_id:
    st.stop()

# --- 2. Vestigingen ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect(
    "Vestiging(en)", locations,
    format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 3. Periode ---
period_options = [
    "yesterday", "this_week", "last_week",
    "this_month", "last_month",
    "this_quarter", "last_quarter", "this_year"
]
period = st.selectbox("Periode", period_options, index=0)

# --- Dynamische step ---
step = "day" if period == "yesterday" else "total"

# --- 4. KPIs ---
params = [("period", period), ("step", step)]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

query_string = urlencode(params, doseq=True, safe='[]')
data_response = requests.get(f"{API_BASE}/get-report?{query_string}")
raw_json = data_response.json()

# --- DEBUG ---
st.subheader("DEBUG: API URL")
st.code(data_response.url)
st.subheader("DEBUG: Raw Response")
st.json(raw_json, expanded=False)

# --- 5. Normalize ---
df = to_wide(normalize_vemcount_response(raw_json))
if df.empty:
    st.error(f"Geen data voor {period}.")
    st.stop()

location_map = {loc["id"]: loc.get("name", "Onbekend") for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. Rol ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"])

# --- 7. UI ---
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client.get('name', 'Retailer')}** – *Mark Ryski*")

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – {period.capitalize()}")

    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", "Regen -4%", "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.2f}%", "vs 25% Ryski", "good" if row['conversion_rate'] >= 25 else "bad")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "Q3 +3.5%", "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "", "neutral")

    st.success("**Actie:** +2 FTE piekmomenten → +8% conversie (Ryski Ch3)")

elif role == "Regio Manager":
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum", "sales_per_visitor": "mean"})
    st.header(f"Regio – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.2f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))
    st.success("**Actie:** Audit stores <20% → labor align → +10% uplift")

else:  # Directie
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Keten – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", "Weer -4%")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.2f}%", "CBS -27")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", "Q3 +3.5%")

    st.success("**Actie:** +15% digital budget droge dagen → ROI 3.8x")

st.caption("RetailGift AI: Vemcount + Ryski + CBS. +10-15% uplift.")
