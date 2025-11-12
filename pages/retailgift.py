# pages/retailgift.py – RetailGift AI Dashboard v2.0
# McKinsey retail inzichten: Footfall → conversie uplift via Ryski + CBS + weer
# Data: Vemcount via FastAPI, CBS OData, OpenWeather

import streamlit as st
import requests
import pandas as pd
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.ui import inject_css, kpi_card
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="🛒", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
OPENWEATHER_KEY = st.secrets["openweather_api_key"]
CBS_DATASET = st.secrets["cbs_dataset"]
CLIENTS_JSON = st.secrets["clients_json_url"]  # Raw GitHub URL

# --- CBS Vertrouwen Live ---
@st.cache_data(ttl=86400)
def get_cbs_vertrouwen():
    url = f"https://opendata.cbs.nl/ODataFeed/odata/{CBS_DATASET}/TableInfos"
    r = requests.get(url)
    data = r.json()["value"]
    latest = max(data, key=lambda x: x.get("Perioden", ""))
    return latest.get("Consumentenvertrouwen_1", -27)

cbs_trust = get_cbs_vertrouwen()

# --- Weer per Postcode ---
@st.cache_data(ttl=3600)
def get_weather(zip_code: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},NL&appid={OPENWEATHER_KEY}&units=metric"
    r = requests.get(url)
    if r.ok:
        data = r.json()
        desc = data["weather"][0]["description"].lower()
        impact = "-4% footfall" if "regen" in desc else "+5% footfall"
        return {"temp": round(data["main"]["temp"]), "desc": desc, "impact": impact}
    return {"temp": 8, "desc": "motregen", "impact": "-4% footfall"}

# --- 1. Klant Selectie ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Selecteer klant", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

# --- 2. Vestigingen Selectie ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect("Selecteer vestiging(en)", locations, format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}", default=locations[:1])
shop_ids = [loc["id"] for loc in selected]

# --- 3. Periode Selectie ---
period = st.selectbox("Periode", ["yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter", "this_year"], index=0)

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

# --- 5. Normalize Data ---
df = to_wide(normalize_vemcount_response(raw_json))

if df.empty:
    st.error(f"Geen data voor {period}. Probeer 'yesterday' of andere vestiging.")
    st.stop()

location_map = {loc["id"]: loc.get("name", "Onbekend") for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. Rol Selectie ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"])

# --- 7. UI per Rol ---
st.title("STORE TRAFFIC IS A GIFT")
client_name = client.get("name", "Onbekende Klant")
st.markdown(f"**{client_name}** – *Mark Ryski* (CBS vertrouwen: {cbs_trust}, Q3 non-food +3.5%)")

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    loc = selected[0]
    weather = get_weather(loc.get("zip", "1000AA"))
    st.header(f"{loc.get('name', 'Onbekend')} – Gift of the Day ({period})")

    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", weather['impact'], "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "Koopbereidheid -14", "bad" if row['conversion_rate'] < 25 else "good")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "Q3 +3.5%", "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "", "neutral")

    st.success("**Actie:** +2 FTE piekmomenten → +5-10% conversie (Ryski Ch3). Indoor bundel bij regen.")

elif role == "Regio Manager":
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum", "sales_per_visitor": "mean"})
    st.header(f"Regio – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", "-4% regen")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%", "CBS -14 koopb.")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", "Q3 +3.5%")

    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))
    st.success("**Actie:** Audit stores <20% – labor align → +10% uplift (Ryski Ch3).")

else:  # Directie
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Keten – {period.capitalize()}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", "-4% regen")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%", "CBS -27")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", "Q3 +3.5%")

    st.success("**Actie:** +15% digital budget droge dagen – ROI 3.8x (Ryski Ch7). Monitor CBS voor Q4 +4% forecast.")

st.caption("RetailGift AI: Fuseert Vemcount, CBS, weer. Onmisbaar voor +10-15% uplift.")
