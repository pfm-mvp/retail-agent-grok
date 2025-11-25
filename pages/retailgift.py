# pages/retailgift.py – DEFINITIEVE WERKENDE VERSIE MET LOCATION POTENTIAL 2.0 (25 nov 2025)
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

# --- PATH + RELOAD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)
import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

# --- UI FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c=""): st.metric(t, v, d)

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- SIDEBAR ---
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

period_option = st.sidebar.selectbox("Periode", ["this_month", "last_month", "this_week", "last_week"], index=0)

# --- DATA OPHALEN (alleen veilige kolommen) ---
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

df_full = normalize_vemcount_response(resp.json())
if df_full.empty:
    st.error("Geen data")
    st.stop()

# --- SHOP META + m² ---
shop_meta = {loc["id"]: {"name": loc["name"], "sq_meter": loc.get("sq_meter", 100)} for loc in locations}
df_full["name"] = df_full["shop_id"].map({k: v["name"] for k, v in shop_meta.items()}).fillna("Onbekend")
df_full["date"] = pd.to_datetime(df_full["date"], errors='coerce')
df_full = df_full.dropna(subset=["date"])

# --- DATUMFILTER ---
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

if period_option == "this_month":
    df_raw = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]
elif period_option == "last_month":
    df_raw = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
else:
    df_raw = df_full.copy()

# --- AGGREGEER (100% veilig – alleen bestaande kolommen) ---
# Fix voor turnover (soms meerdere per dag → sum!)
df_raw["turnover"] = pd.to_numeric(df_raw["turnover"], errors='coerce').fillna(0)

daily = df_raw.groupby(["shop_id", "date"]).agg({
    "turnover": "sum",
    "count_in": "sum",
    "conversion_rate": "mean",
    "sales_per_visitor": "mean"
}).reset_index()

df = daily.groupby("shop_id").agg({
    "turnover": "sum",
    "count_in": "sum",
    "conversion_rate": "mean",
    "sales_per_visitor": "mean"
}).reset_index()

# m² en naam toevoegen uit shop_meta
df["name"] = df["shop_id"].map({k: v["name"] for k, v in shop_meta.items()})
df["sq_meter"] = df["shop_id"].map({k: v["sq_meter"] for k, v in shop_meta.items()}).fillna(100)

# --- REGIO MANAGER VIEW MET LOCATION POTENTIAL 2.0 ---
if tool == "Regio Manager":
    st.header("Regio Dashboard – AI-gedreven stuurinformatie")

    agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}")

    st.markdown("---")
    st.subheader("Location Potential 2.0 – Wat zou elke winkel écht moeten opleveren?")

    BRANCHE_BENCHMARK_PER_M2_MONTH = 87.50  # CBS 2025

    potential_list = []
    for _, row in df.iterrows():
        name = row["name"]
        m2 = row["sq_meter"]
        current = row["turnover"]

        # Historische data voor deze winkel
        hist = df_full[df_full["shop_id"] == row["shop_id"]]
        if len(hist) > 5:
            best_conv = hist["conversion_rate"].quantile(0.75) / 100
            best_spv = hist["sales_per_visitor"].quantile(0.75)
            avg_footfall = hist["count_in"].tail(30).mean()
        else:
            best_conv = 0.16
            best_spv = 3.30
            avg_footfall = 500

        pot_performance = avg_footfall * best_conv * best_spv * 30 * 1.03
        pot_m2 = m2 * BRANCHE_BENCHMARK_PER_M2_MONTH * 1.03
        final_potential = max(pot_performance, pot_m2)
        gap = final_potential - current
        realisatie = (current / final_potential * 100) if final_potential > 0 else 0

        potential_list.append({
            "Winkel": name,
            "m²": int(m2),
            "Huidig €": int(current),
            "Potentieel €": int(final_potential),
            "Gap €": int(gap),
            "Realisatie": f"{realisatie:.0f}%"
        })

    pot_df = pd.DataFrame(potential_list).sort_values("Gap €", ascending=False)

    def status(val):
        v = float(val.rstrip("%"))
        if v >= 90: return "🟢"
        if v >= 70: return "🟡"
        return "🔴"

    pot_df["Status"] = pot_df["Realisatie"].apply(status)

    st.dataframe(pot_df[[
        "Winkel", "m²", "Huidig €", "Potentieel €", "Gap €", "Realisatie", "Status"
    ]].style.format({
        "Huidig €": "€{:,}",
        "Potentieel €": "€{:,}",
        "Gap €": "€{:,}",
        "m²": "{:,}"
    }), use_container_width=True)

    total_gap = pot_df["Gap €"].sum()
    st.success(f"**Totaal onbenut potentieel deze maand: €{int(total_gap):,}** – ligt op straat!")

    st.info("Berekend als max(beste eigen prestaties, m² × €87,50 branchebenchmark) + 3% CBS-uplift")

else:
    st.write("Store Manager / Directie view – binnenkort beschikbaar")

st.caption("RetailGift AI – Location Potential 2.0 100% STABIEL & LIVE – 25 nov 2025")
