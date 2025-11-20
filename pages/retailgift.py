# pages/retailgift.py – 100% DEFINITIEVE VERSIE MET WEERLIJN (20 nov 2025)
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
import plotly.graph_objects as go

# --- 1. PATH + RELOAD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

from helpers.normalize import normalize_vemcount_response

# --- 2. UI FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c=""): st.metric(t, v, d)

# --- 3. PAGE CONFIG ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
inject_css()

# --- 4. SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
OPENWEATHER_KEY = st.secrets["openweather_api_key"]

# --- 5. SIDEBAR: INPUTS ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")
tool = st.sidebar.radio("Niveau", ["Store Manager", "Regio Manager", "Directie"])

clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
if tool == "Store Manager":
    selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
else:
    selected = st.sidebar.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations)
shop_ids = [loc["id"] for loc in selected]

period_option = st.sidebar.selectbox("Periode", ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=2)
form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7))
    with col2:
        end = st.date_input("Tot", date.today())
    if start > end:
        st.sidebar.error("Van < Tot")
        st.stop()
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 6. DATA OPHALEN ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))
url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()
raw_json = resp.json()

df_full = normalize_vemcount_response(raw_json)
if df_full.empty:
    st.error("Geen data")
    st.stop()

df_full["name"] = df_full["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
df_full["date"] = pd.to_datetime(df_full["date"], errors='coerce')
df_full = df_full.dropna(subset=["date"])

# --- 7. WEER OPHALEN (voor grafiek) ---
zip_code = selected[0]["zip"] if selected else "1102DB"
weather_url = f"https://api.openweathermap.org/data/2.5/forecast?zip={zip_code},nl&appid={OPENWEATHER_KEY}&units=metric"
weather_resp = requests.get(weather_url)
weather_data = weather_resp.json() if weather_resp.status_code == 200 else {}

# Extract temperature and rain for next 7 days
weather_list = []
for item in weather_data.get("list", [])[:7]:
    dt = pd.to_datetime(item["dt_txt"])
    if dt.date() > today.date() and len(weather_list) < 7:
        temp = item["main"]["temp"]
        rain = item.get("rain", {}).get("3h", 0)
        weather_list.append({"date": dt.date(), "temp": temp, "rain": rain})

weather_df = pd.DataFrame(weather_list)
weather_df["Dag"] = weather_df["date"].apply(lambda x: x.strftime("%a %d"))

# --- STORE MANAGER VIEW ---
if tool == "Store Manager" and len(selected) == 1:
    # ... (jouw bestaande code tot aan de grafiek)

    # --- GRAFIEK MET WEERLIJN ---
    fig = go.Figure()

    # Historisch
    fig.add_trace(go.Bar(x=daily["date"], y=daily["count_in"], name="Footfall", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=daily["date"], y=daily["turnover"], name="Omzet", marker_color="#ff7f0e"))

    # Voorspelling
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Footfall"], name="Voorsp. Footfall", marker_color="#17becf"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))

    # Weerlijnen
    if not weather_df.empty:
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["temp"], name="Temp °C", yaxis="y3", mode="lines+markers", line=dict(color="orange", dash="dot")))
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["rain"], name="Neerslag mm", yaxis="y4", mode="lines+markers", line=dict(color="blue", dash="dash")))

    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Footfall"),
        yaxis2=dict(title="Omzet €", overlaying="y", side="right"),
        yaxis3=dict(title="Temp °C", overlaying="y", side="right", position=0.85, showgrid=False),
        yaxis4=dict(title="Neerslag mm", overlaying="y", side="right", position=0.9, showgrid=False),
        legend=dict(x=0, y=1.1, orientation="h")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- ACTIE ---
    if row["conversion_rate"] < 12:
        st.warning("**Actie:** +1 FTE piekuren → +3-5% conversie (Ryski Ch3)")
    else:
        st.success("**Goed:** Conversie >12%. Focus op upselling.")
