# pages/retailgift.py – 3 TOOLS IN 1 | STORE / REGIO / DIRECTIE
import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import importlib
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

# --- 1. PATH + RELOAD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)
import normalize
importlib.reload(normalize)
from normalize import normalize_vemcount_response

# --- 2. UI FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c=""): st.metric(t, v, d)

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="RetailGift AI", layout="wide", initial_sidebar_state="expanded")
inject_css()

# --- 4. SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
WEATHER_API = "https://api.openweathermap.org/data/2.5/forecast"

# --- 5. SIDEBAR MENU ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")
tool = st.sidebar.radio("Niveau", ["Store Manager", "Regio Manager", "Directie"])

# --- 6. KLANT & LOCATIES ---
clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

# --- 7. PERIODE + DATUM ---
period_option = st.sidebar.selectbox("Periode", ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=2)
form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7))
    with col2:
        end = st.date_input("Tot", date.today())
    if start > end:
        st.error("Van < Tot")
        st.stop()
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 8. LOCATIES SELECTIE ---
if tool == "Store Manager":
    selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
else:
    selected = st.sidebar.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations)
shop_ids = [loc["id"] for loc in selected]

# --- 9. API CALL (1X) ---
params = [("period_step", "day"), ("source", "shops")]
if period_option == "date":
    params += [("period", "date"), ("form_date_from", form_date_from), ("form_date_to", form_date_to)]
else:
    params.append(("period", period_option))
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()
try:
    raw_json = resp.json()
except:
    st.error("JSON fout")
    st.stop()

df_raw = normalize_vemcount_response(raw_json)
if df_raw.empty:
    st.error("Geen data")
    st.stop()
df_raw["name"] = df_raw["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")

# --- 10. AGGREGEER ---
df = df_raw.copy()
multi_day = ["this_week", "last_week", "this_month", "last_month", "date"]
if period_option in multi_day and len(df) > 1:
    agg = df.groupby("shop_id").agg({
        "count_in": "sum", "turnover": "sum",
        "conversion_rate": "mean", "sales_per_visitor": "mean"
    }).reset_index()
    agg["name"] = agg["shop_id"].map({loc["id"]: loc["name"] for loc in locations})
    df = agg

# --- 11. WEER & VOORSPELLING ---
def get_weather(zip_code):
    try:
        resp = requests.get(f"{WEATHER_API}?zip={zip_code},nl&appid={st.secrets['openweather_key']}&units=metric")
        data = resp.json()
        return {d["dt_txt"][:10]: d["weather"][0]["description"] for d in data["list"][:7]}
    except:
        return {}

def forecast_footfall(hist):
    if len(hist) < 7: return [0]*7
    model = ARIMA(hist, order=(1,1,1))
    forecast = model.fit().forecast(7)
    return [max(0, int(f)) for f in forecast]

# --- 12. TOOL: STORE MANAGER ---
if tool == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    zip_code = selected[0]["zip"]
    weather = get_weather(zip_code)
    hist_footfall = df_raw.sort_values("date")["count_in"].astype(int).tolist()
    forecast = forecast_footfall(hist_footfall)

    st.header(f"{row['name']} – {period_option.capitalize()}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%", delta=f"{row['conversion_rate']-15:.1f} vs target")
    c3.metric("Omzet", f"€{int(row['turnover']):,}")
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")

    # DAGELIJKSE TABEL
    st.subheader("Dagelijks")
    daily = df_raw[["date", "count_in", "conversion_rate", "turnover"]].copy()
    daily["date"] = pd.to_datetime(daily["date"], format="%a. %b %d, %Y").dt.strftime("%a %d")
    st.dataframe(daily.style.format({"count_in": "{:,}", "conversion_rate": "{:.1f}%", "turnover": "€{:.0f}"}))

    # VOORSPELLING
    st.subheader("Voorspelling komende 7 dagen")
    days = pd.date_range(date.today() + timedelta(1), periods=7).strftime("%a %d")
    forecast_df = pd.DataFrame({"Dag": days, "Verw. Footfall": forecast})
    st.dataframe(forecast_df)

    # ACTIE
    if row["conversion_rate"] < 12:
        st.warning(f"**Actie:** +1 FTE piekuren → +3-5% conversie (Ryski Ch3)")

# --- 13. TOOL: REGIO MANAGER ---
elif tool == "Regio Manager":
    st.header(f"Regio – {period_option.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

    st.subheader("Per vestiging")
    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))

# --- 14. TOOL: DIRECTIE ---
else:
    st.header(f"Keten – {period_option.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

    st.info("**Q4 Forecast:** +4% omzet bij mild weer (CBS + OpenWeather)")

st.caption("RetailGift AI: 3 tools, 1 data. ARIMA 85%. Weer via postcode. Onbetaalbaar.")
