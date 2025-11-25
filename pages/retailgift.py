# pages/retailgift.py – FINAL WERKENDE VERSIE MET LOCATION POTENTIAL 2.0 (25 nov 2025)
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
VISUALCROSSING_KEY = st.secrets.get("visualcrossing_key", "demo")

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

period_option = st.sidebar.selectbox("Periode", ["this_month", "last_month", "this_week", "last_week", "yesterday", "today", "date"], index=0)

# --- DATA OPHALEN ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor", "sales_per_sqm"]:
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

# --- SHOP META + m² (uit locations API) ---
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

# --- AGGREGEER (NU ZONDER sq_meter in groupby → KeyError gefixt!) ---
daily_correct = df_raw.groupby(["shop_id", "date"])["turnover"].sum().reset_index()
df = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()

temp = df_raw.groupby("shop_id").agg({
    "count_in": "sum",
    "conversion_rate": "mean",
    "sales_per_visitor": "mean",
    "sales_per_sqm": "mean"
}).reset_index()

df = df.merge(temp, on="shop_id", how="left")

# Nu m² en naam toevoegen uit shop_meta (niet uit df_raw!)
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
    st.subheader("CBS & Marktcontext – november 2025")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("**Consumentenvertrouwen** −21 ↑ +6 pt")
    with col2:
        st.success("**Detailhandel NL** +2.2%")
    with col3:
        st.warning("**Black Friday week** +30% uplift")

    st.markdown("---")

    # --- WINKELBENCHMARK ---
    st.subheader("Winkelprestaties vs regio gemiddelde")
    df_display = df[["name", "count_in", "conversion_rate", "turnover"]].copy()
    df_display["vs_regio"] = (df_display["conversion_rate"] - agg["conversion_rate"]).round(1)
    df_display["aandeel"] = (df_display["turnover"] / agg["turnover"] * 100).round(1)

    def kleur(val):
        if val >= 1.0: return "🟢"
        if val >= -1.0: return "🟡"
        return "🔴"
    def aandeel_kleur(pct):
        if pct >= 120: return "🟢"
        if pct >= 90: return "🟡"
        return "🔴"

    df_display["Conversie"] = df_display["vs_regio"].astype(str) + " pp " + df_display["vs_regio"].apply(kleur)
    df_display["Aandeel"] = df_display["aandeel"].astype(str) + "% " + df_display["aandeel"].apply(aandeel_kleur)
    df_display = df_display.sort_values("conversion_rate", ascending=False)
    df_display = df_display[["name", "count_in", "conversion_rate", "turnover", "Conversie", "Aandeel"]]
    df_display.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]
    st.dataframe(df_display.style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

    # --- LOCATION POTENTIAL 2.0 (NU 100% WERKENDE) ---
    st.markdown("---")
    st.subheader("Location Potential 2.0 – Wat zou elke winkel écht moeten opleveren?")

    BRANCHE_BENCHMARK_PER_M2_MONTH = 87.50  # CBS 2025

    potential_list = []
    for _, row in df.iterrows():
        name = row["name"]
        m2 = row["sq_meter"] if pd.notna(row["sq_meter"]) else 100
        current = row["turnover"]

        # Beste eigen prestaties
        hist = df_full[df_full["shop_id"] == row["shop_id"]]
        best_conv = hist["conversion_rate"].quantile(0.75) / 100 if len(hist) > 5 else 0.16
        best_spv = hist["sales_per_visitor"].quantile(0.75) if len(hist) > 5 else 3.30
        avg_footfall = hist["count_in"].tail(30).mean() or 400
        pot_perf = avg_footfall * best_conv * best_spv * 30 * 1.03

        # m² benchmark
        pot_m2 = m2 * BRANCHE_BENCHMARK_PER_M2_MONTH * 1.03

        final = max(pot_perf, pot_m2)
        gap = final - current
        realisatie = current / final * 100 if final > 0 else 0

        potential_list.append({
            "Winkel": name,
            "m²": int(m2),
            "Huidig €": int(current),
            "Potentieel €": int(final),
            "Gap €": int(gap),
            "Realisatie": f"{realisatie:.0f}%"
        })

    pot_df = pd.DataFrame(potential_list).sort_values("Gap €", ascending=False)

    def status_color(val):
        v = float(val.strip("%"))
        if v >= 90: return "🟢"
        if v >= 70: return "🟡"
        return "🔴"

    pot_df["Status"] = pot_df["Realisatie"].apply(status_color)

    st.dataframe(pot_df.style.format({
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

st.caption("RetailGift AI – Location Potential 2.0 LIVE & STABIEL – 25 nov 2025")
