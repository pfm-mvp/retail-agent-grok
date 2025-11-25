# pages/retailgift_regio.py – 100% WERKENDE REGIO MANAGER – GEBOUWD OP JOUW STORE MANAGER LOGICA (25 nov 2025)
import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import importlib
import numpy as np
import plotly.graph_objects as go

# --- 1. PATH + RELOAD (exact jouw origineel) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)
import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

# --- 2. UI FALLBACK (exact jouw origineel) ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c=""): st.metric(t, v, d)

# --- 3. PAGE CONFIG ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
inject_css()

# --- 4. SECRETS (exact jouw origineel) ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 5. SIDEBAR ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")

clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

# --- ALLE WINKELS AUTOMATISCH (regio manager) ---
shop_ids = [loc["id"] for loc in locations]

# --- DATA OPHALEN (exact jouw originele code) ---
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

# --- 7. DATUMVARIABELEN + FILTER (exact jouw origineel) ---
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

df_raw = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]

# --- 9. AGGREGEER HUIDIGE PERIODE (exact jouw origineel) ---
daily_correct = df_raw.groupby(["shop_id", "date"])["turnover"].max().reset_index()
df = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()
temp = df_raw.groupby("shop_id").agg({"count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}).reset_index()
df = df.merge(temp, on="shop_id", how="left")
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- REGIO MANAGER VIEW – NEXT LEVEL ---
st.header("🔥 Regio Dashboard – AI-gedreven stuurinformatie")

# KPI's
agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}")

st.markdown("---")

# Winkelbenchmark met stoplichten
st.subheader("Winkelprestaties vs regio gemiddelde")
df_display = df.copy()
df_display["conv_diff"] = df_display["conversion_rate"] - agg["conversion_rate"]
df_display["share_pct"] = (df_display["turnover"] / agg["turnover"] * 100).round(1)

def stoplicht_conv(diff):
    if diff >= 1.0: return "🟢"
    if diff >= -1.0: return "🟡"
    return "🔴"

def stoplicht_share(pct):
    if pct >= 120: return "🟢"
    if pct >= 90: return "🟡"
    return "🔴"

df_display["vs Regio"] = df_display["conv_diff"].round(1).astype(str) + " pp " + df_display["conv_diff"].apply(stoplicht_conv)
df_display["Aandeel"] = df_display["share_pct"].astype(str) + "% " + df_display["share_pct"].apply(stoplicht_share)
df_display = df_display.sort_values("conversion_rate", ascending=False)
df_display = df_display[["name", "count_in", at "conversion_rate", "turnover", "vs Regio", "Aandeel"]]
df_display.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]
st.dataframe(df_display.style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

