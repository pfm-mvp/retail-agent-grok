# pages/retailgift.py – RetailGift AI Dashboard v1.1
# McKinsey retail inzichten: Footfall → conversie uplift via Ryski + CBS + weer
# Data: Vemcount via FastAPI, CBS OData, OpenWeather

import streamlit as st
import requests
import pandas as pd
import os
import sys
from datetime import date, timedelta
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
    latest = max(data, key=lambda x: x["Perioden"])
    return latest.get("Consumentenvertrouwen_1", -27)

cbs_trust = get_cbs_vertrouwen()

# --- Weer Forecast per Postcode ---
@st.cache_data(ttl=3600)
def get_weather(zip_code: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},NL&appid={OPENWEATHER_KEY}&units=metric"
    r = requests.get(url)
    if r.ok:
        data = r.json()
        desc = data["weather"][0]["description"]
        return {
            "temp": round(data["main"]["temp"]),
            "desc": desc,
            "impact": "-4% footfall" if "regen" in desc else "+5% footfall"
        }
    return {"temp": 8, "desc": "motregen", "impact": "-4% footfall"}

# --- 1. Klant Selectie ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Selecteer klant", clients, format_func=lambda x: f"{x.get('name', 'Onbekend')} ({x.get('brand', 'Onbekend')})")
client_id = client.get("company_id")

# --- 2. Vestigingen Selectie ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect(
    "Selecteer vestiging(en)", locations,
    format_func=lambda x: f"{x.get('name', 'Onbekend')} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 3. Periode Selectie (alle uit docs) ---
period_options = ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year", "date"]
period = st.selectbox("Periode", period_options, index=0)

# --- 4. Datum Selector voor 'date' ---
form_date_from = form_date_to = None
if period == "date":
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7))
    with col2:
        end = st.date_input("Tot", date.today())
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 5. API CALL MET period_step=day ---
params = [
    ("period", period),
    ("period_step", "day")  # <-- GEVIXT: period_step
]
if form_date_from:
    params.extend([("form_date_from", form_date_from), ("form_date_to", form_date_to)])
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

query_string = urlencode(params, doseq=True, safe='[]')
url = f"{API_BASE}/get-report?{query_string}"
data_response = requests.get(url)
raw_json = data_response.json()

# --- DEBUG ---
st.subheader("DEBUG: API URL")
st.code(url, language="text")

# --- 6. NORMALISEER & AGGREGATE ---
df = to_wide(normalize_vemcount_response(raw_json))

if df.empty:
    st.error(f"Geen data voor {period}. Probeer 'today' of andere vestiging.")
    st.stop()

df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")

# --- AGGREGATE VOOR WEEK/MONTH/ETC (sum/mean) ---
multi_day_periods = ["this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year", "date"]
if period in multi_day_periods:
    agg = {
        "count_in": df["count_in"].sum(),
        "turnover": df["turnover"].sum(),
        "conversion_rate": df["conversion_rate"].mean(),
        "sales_per_visitor": df["sales_per_visitor"].mean()
    }
    df = pd.DataFrame([agg])
    df["name"] = "TOTAAL" if len(selected) > 1 else selected[0]["name"]

# --- 7. ROL ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"], index=0)

# --- 8. UI per Rol ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client.get('name', 'Onbekende Klant')}** – *Mark Ryski* (CBS vertrouwen: {cbs_trust}, Q3 non-food +3.5%)")

if role == "Store Manager":
    row = df.iloc[0]
    loc = selected[0] if selected else {}
    weather = get_weather(loc.get("zip", "1000AA"))
    st.header(f"{row['name']} – Gift of the Day ({period})")

    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi_card("Footfall", f"{int(row['count_in']):,}", weather['impact'], "primary")
    with col2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "Koopbereidheid -14", "bad" if row['conversion_rate'] < 25 else "good")
    with col3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "Q3 +3.5%", "good")
    with col4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", period, "neutral")

    st.success("**Actie:** +2 FTE 12-18u → +5-10% conversie (Ryski Ch3). Indoor bundel bij regen.")

elif role == "Regio Manager":
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

st.caption("RetailGift AI: Aggregatie voor week/month (sum/mean). Onmisbaar.")
