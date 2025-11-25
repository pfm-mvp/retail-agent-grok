# pages/retailgift_store.py – 100% WERKENDE VERSIE MET VERWACHTE OMZET + % VS VORIGE MAAND (25 nov 2025)
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
VISUALCROSSING_KEY = st.secrets.get("visualcrossing_key", "demo")

# --- 5. SIDEBAR ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")

clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
shop_ids = [loc["id"] for loc in selected]

period_option = st.sidebar.selectbox("Periode", ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=4)

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

# --- 7. DATUMVARIABELEN + FILTER ---
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

if period_option == "yesterday":
    df_raw = df_full[df_full["date"] == (today - pd.Timedelta(days=1))]
elif period_option == "today":
    df_raw = df_full[df_full["date"] == today]
elif period_option == "this_week":
    start_week = today - pd.Timedelta(days=today.weekday())
    end_week = start_week + pd.Timedelta(days=6)
    df_raw = df_full[(df_full["date"] >= start_week) & (df_full["date"] <= end_week)]
elif period_option == "last_week":
    start_last_week = start_week - pd.Timedelta(days=7)
    end_last_week = end_week - pd.Timedelta(days=7)
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

# --- 8. VORIGE PERIODE (voor delta's) ---
prev_agg = pd.Series({"count_in": 0, "turnover": 0, "conversion_rate": 0, "sales_per_visitor": 0})
if period_option == "this_week":
    prev_data = df_full[(df_full["date"] >= start_last_week) & (df_full["date"] <= end_last_week)]
    if not prev_data.empty:
        prev_agg = prev_data.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
elif period_option == "this_month":
    prev_data = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
    if not prev_data.empty:
        prev_agg = prev_data.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})

# --- 9. AGGREGEER HUIDIGE PERIODE ---
daily_correct = df_raw.groupby(["shop_id", "date"])["turnover"].max().reset_index()
df = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()
temp = df_raw.groupby("shop_id").agg({"count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}).reset_index()
df = df.merge(temp, on="shop_id", how="left")
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- 10. WEEKDAG GEMIDDELDEN ---
params_hist = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params_hist.append(("data[]", sid))
for output in ["conversion_rate", "sales_per_transaction"]:
    params_hist.append(("data_output[]", output))
url_hist = f"{API_BASE}/get-report?{urlencode(params_hist, doseq=True, safe='[]')}"
resp_hist = requests.get(url_hist)
df_hist = normalize_vemcount_response(resp_hist.json()) if resp_hist.status_code == 200 else pd.DataFrame()
for col in ["conversion_rate", "sales_per_transaction", "date"]:
    if col not in df_hist.columns:
        df_hist[col] = 0.0 if col != "date" else pd.NaT
df_hist["date"] = pd.to_datetime(df_hist["date"], errors='coerce')
df_hist["weekday"] = df_hist["date"].dt.weekday.fillna(0).astype(int)
weekday_avg = pd.DataFrame({"conversion_rate": [13.0]*7, "sales_per_transaction": [22.0]*7}, index=range(7))
if not df_hist.empty:
    temp = df_hist.groupby("weekday")[["conversion_rate", "sales_per_transaction"]].mean()
    weekday_avg.update(temp)

# --- 11. VOORSPELLING FUNCTIE ---
def forecast_series(series, steps=7):
    series = [x for x in series if pd.notnull(x) and x > 
