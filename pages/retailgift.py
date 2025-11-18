# pages/retailgift.py – 3 NIVEAUS + VOORSPELLING + GRAFIEKEN + WEEKDAG-GEMIDDELDEN
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
import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

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

# Klant
clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

# Locaties
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
if tool == "Store Manager":
    selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
else:
    selected = st.sidebar.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations)
shop_ids = [loc["id"] for loc in selected]

# Periode
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

# --- 6. API CALL – ALTIJD this_year ---
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

# --- 7. NORMALISEER + DATE FIX ---
df_full = normalize.normalize_vemcount_response(raw_json)  # ← NU df_full = volledige data
if df_full.empty:
    st.error("Geen data")
    st.stop()
df_full["name"] = df_full["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
df_full["date"] = pd.to_datetime(df_full["date"], errors='coerce')
df_full = df_full.dropna(subset=["date"])

# --- 8. DATUMVARIABELEN ---
today = pd.Timestamp.today().normalize()
start_week = today - pd.Timedelta(days=today.weekday())
end_week = start_week + pd.Timedelta(days=6)
start_last_week = start_week - pd.Timedelta(days=7)
end_last_week = end_week - pd.Timedelta(days=7)
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

# --- 9. FILTER OP GEKOZEN PERIODE (op volledige data) ---
if period_option == "yesterday":
    df_raw = df_full[df_full["date"] == (today - pd.Timedelta(days=1))]
elif period_option == "today":
    df_raw = df_full[df_full["date"] == today]
elif period_option == "this_week":
    df_raw = df_full[(df_full["date"] >= start_week) & (df_full["date"] <= end_week)]
elif period_option == "last_week":
    df_raw = df_full[(df_full["date"] >= start_last_week) & (df_full["date"] <= end_last_week)]
elif period_option == "this_month":
    df_raw = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]
elif period_option == "last_month":
    df_raw = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
elif period_option == "date":
    start = pd.to_datetime(form_date_from)
    end = pd.to_datetime(form_date_to)
    df_raw = df_full[(df_full["date"] >= start) & (df_full["date"] <= end)]
else:
    df_raw = df_full.copy()

# --- 10. VORIGE PERIODE BEREKENEN OP VOLLEDIGE DATA (df_full) ---
prev_start = prev_end = None
if period_option == "last_week":
    prev_start = start_last_week - pd.Timedelta(days=7)
    prev_end   = end_last_week - pd.Timedelta(days=7)
elif period_option == "this_week":
    prev_start = start_last_week
    prev_end   = end_last_week
elif period_option == "this_month":
    prev_start = first_of_last_month
    prev_end   = first_of_month - pd.Timedelta(days=1)
elif period_option == "last_month":
    prev_start = first_of_last_month - pd.DateOffset(months=1)
    prev_end   = first_of_last_month - pd.Timedelta(days=1)
elif period_option == "date":
    length = (pd.to_datetime(form_date_to) - pd.to_datetime(form_date_from)).days + 1
    prev_start = pd.to_datetime(form_date_from) - pd.Timedelta(days=length)
    prev_end   = pd.to_datetime(form_date_from) - pd.Timedelta(days=1)

if prev_start and prev_end:
    prev_data = df_full[(df_full["date"] >= prev_start) & (df_full["date"] <= prev_end)]
    prev_agg = prev_data.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}) if not prev_data.empty else pd.Series({"count_in": 0, "turnover": 0, "conversion_rate": 0, "sales_per_visitor": 0})
else:
    prev_agg = pd.Series({"count_in": 0, "turnover": 0, "conversion_rate": 0, "sales_per_visitor": 0})

# --- 11. AGGREGEER HUIDIGE PERIODE ---
df = df_raw.groupby("shop_id").agg({
    "count_in": "sum", "turnover": "sum",
    "conversion_rate": "mean", "sales_per_visitor": "mean"
}).reset_index()
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- WEEKDAG-GEMIDDELDEN (ongewijzigd) ---
# ... jouw bestaande code vanaf lijn 10 blijft exact hetzelfde ...

# --- 12. STORE MANAGER ---
if tool == "Store Manager" and len(selected) == 1:
    if df.empty:
        st.error("Geen data beschikbaar voor deze winkel en periode.")
        st.stop()
    row = df.iloc[0]

    def calc_delta(curr, key):
        prev = prev_agg.get(key, 0)
        if prev == 0 or pd.isna(prev):
            return "N/A"
        pct = (curr - prev) / prev * 100
        return f"{pct:+.1f}%"

    st.header(f"{row['name']} – {period_option.replace('_', ' ').title()}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall",   f"{int(row['count_in']):,}",      calc_delta(row['count_in'], 'count_in'))
    c2.metric("Conversie",  f"{row['conversion_rate']:.1f}%", calc_delta(row['conversion_rate'], 'conversion_rate'))
    c3.metric("Omzet",      f"€{int(row['turnover']):,}",     calc_delta(row['turnover'], 'turnover'))
    c4.metric("SPV",        f"€{row['sales_per_visitor']:.2f}", calc_delta(row['sales_per_visitor'], 'sales_per_visitor'))

    # De rest van jouw Store Manager code (dagelijks, voorspelling, grafiek, actie) blijft 100% ongewijzigd
    # Je kunt alles onder dit punt gewoon laten zoals het was – het werkt allemaal
    # Ik laat het hier weg voor overzicht, maar je kopieert gewoon jouw bestaande code terug

    # --- DAGELIJKSE TABEL, VOORSPELLING, GRAFIEK, ACTIE – JOUW CODE ---
    # (plak hier jouw originele code vanaf "st.subheader("Dagelijks")" tot einde)
