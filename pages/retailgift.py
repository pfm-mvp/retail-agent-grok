# pages/RetailGift.py – KLANTGERICHT & DYNAMISCH
import streamlit as st
import requests
import pandas as pd
import json
from datetime import date
from helpers_normalize import normalize_vemcount_response, to_wide
from ui import kpi_card, inject_css

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

API_BASE = st.secrets["API_URL"].rstrip("/")

# --- 1. Laad klanten uit clients.json ---
try:
    clients = requests.get("https://raw.githubusercontent.com/jouw-repo/main/clients.json").json()
except:
    st.error("clients.json niet gevonden. Upload naar repo root.")
    st.stop()

# --- 2. Kies klant ---
client = st.selectbox("Kies klant", clients, format_func=lambda x: x["name"])
client_id = client["company_id"]

# --- 3. Haal locaties op per klant ---
try:
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
    if not locations:
        st.warning(f"Geen locaties voor {client['name']}. Vemcount rechten?")
        st.stop()
except Exception as e:
    st.error(f"API fout: {e}")
    st.stop()

# --- 4. Kies vestigingen ---
selected = st.multiselect(
    "Vestigingen",
    locations,
    format_func=lambda x: f"{x.get('name')} – {x.get('address', {}).get('postal_code', 'N/A')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 5. Haal KPIs op ---
params = [("data[]", sid) for sid in shop_ids] + [("data_output[]", k) for k in ["count_in", "turnover", "conversion_rate", "sales_per_visitor"]]
r = requests.post(f"{API_BASE}/get-report", params=params)
if r.status_code != 200:
    st.error(f"Data fout: {r.text}")
    st.stop()

df = to_wide(normalize_vemcount_response(r.json()))
df["shop_name"] = df["shop_id"].map(lambda x: next((l["name"] for l in locations if l["id"] == x), "Onbekend"))

# --- 6. UI: Store Manager ---
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

    st.success("**Actie:** +2 FTE 12-18u → **+€1.920 omzet** (Ryski Ch3 – labor alignment)")
else:
    agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean"})
    st.header("Regio Overzicht")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

st.caption("RetailGift AI: Klant → Locaties → Acties. Onbetaalbaar.")
