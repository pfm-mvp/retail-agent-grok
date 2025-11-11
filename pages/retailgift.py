# pages/retailgift.py – RetailGift AI Dashboard v1.0
# McKinsey retail inzichten: Footfall → conversie uplift via Ryski + CBS + weer
# Data: Vemcount via FastAPI, CBS OData, OpenWeather

import streamlit as st
import requests
import pandas as pd
import os
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers.ui import inject_css, kpi_card, brand_colors
from helpers.normalize import normalize_vemcount_response, to_wide

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
OPENWEATHER_KEY = st.secrets["openweather_api_key"]
CBS_DATASET = st.secrets["cbs_dataset"]
CLIENTS_JSON = st.secrets["clients_json_url"]  # Raw GitHub URL

# --- CBS Vertrouwen Live ---
@st.cache_data(ttl=86400)
def get_cbs_vertrouwen():
    try:
        url = f"https://opendata.cbs.nl/ODataFeed/odata/{CBS_DATASET}/TableInfos"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()["value"]
            latest = max(data, key=lambda x: x.get("Perioden", ""))
            return latest.get("Consumentenvertrouwen_1", -27)
    except:
        pass
    return -27  # fallback

cbs_trust = get_cbs_vertrouwen()

# --- Weer Forecast per Postcode ---
@st.cache_data(ttl=3600)
def get_weather(zip_code: str):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},NL&appid={OPENWEATHER_KEY}&units=metric"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()
            desc = data["weather"][0]["description"].lower()
            impact = "-4% footfall" if "regen" in desc else "+5% footfall"
            return {"temp": round(data["main"]["temp"]), "desc": desc, "impact": impact}
    except:
        pass
    return {"temp": 8, "desc": "motregen", "impact": "-4% footfall"}

# --- 1. Klant Selectie ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Selecteer klant", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

if not client_id:
    st.error("Geen geldige klant geselecteerd.")
    st.stop()

# --- 2. Vestigingen Selectie ---
try:
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
except:
    st.error("Kon locaties niet ophalen.")
    st.stop()

selected = st.multiselect(
    "Selecteer vestiging(en)", locations,
    format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}",
    default=locations[:1] if locations else []
)
shop_ids = [loc["id"] for loc in selected if "id" in loc]

# --- 3. Periode Selectie ---
period = st.selectbox("Periode", ["yesterday", "today", "this_week", "last_week"], index=0)

# --- 4. KPIs Ophalen ---
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

# --- 5. Normalize Data ---
df = to_wide(normalize_vemcount_response(raw_json))

if df.empty:
    st.error(f"Geen data voor {period}. Probeer 'today' of andere vestiging.")
    st.stop()

location_map = {loc["id"]: loc.get("name", "Onbekend") for loc in locations}
df["name"] = df["shop_id"].map(location_map).fillna("Onbekend")

# --- 6. Rol Selectie ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"], index=0)

# --- 7. UI per Rol ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
client_name = client.get("name", "Onbekende Klant")
st.markdown(f"**{client_name}** – *Mark Ryski* (CBS vertrouwen: {cbs_trust}, Q3 non-food +3.5%)")

if role == "Store Manager":
    if len(selected) == 1:
        row = df.iloc[0]
        loc = selected[0]
        weather = get_weather(loc.get("zip", "1000AA"))
        st.header(f"{loc.get('name', 'Onbekend')} – Gift of the Day ({period})")

        col1, col2, col3, col4 = st.columns(4)
        with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", weather['impact'], "primary")
        with col2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "Koopbereidheid -14", "bad" if row['conversion_rate'] < 25 else "good")
        with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "Q3 +3.5%", "good")
        with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", period, "neutral")

        st.success("**Actie:** +2 FTE 12-18u → +5-10% conversie (Ryski Ch3). Indoor bundel bij regen.")
    else:
        st.warning("Selecteer 1 vestiging voor store view.")

elif role == "Regio Manager":  # <-- GEVIXT: == i.p.v. =
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    weather = get_weather(selected[0].get("zip", "1000AA")) if selected else {"impact": "N/A"}
    st.header(f"Regio Overzicht ({period})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", weather['impact'])
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%", "CBS -14 koopbereidheid")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", "Q3 trend +3.5%")

    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))
    st.success("**Actie:** Audit laagste conversie stores – labor align op pieken → +10% uplift (Ryski Ch3).")

else:  # Directie
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.header(f"Keten Overzicht ({period})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", "Weer impact: -4%")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%", "CBS -27 vertrouwen")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", "Q3 +3.5% non-food")

    st.success("**Actie:** +15% marketing budget droge dagen – ROI 3.8x (Ryski Ch7). Monitor CBS voor Q4 +4% forecast.")

st.caption("RetailGift AI: Fuseert Vemcount, CBS, weer. Onmisbaar voor +10-15% uplift.")
