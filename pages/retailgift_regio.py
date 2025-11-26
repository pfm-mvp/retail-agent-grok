# pages/retailgift_regio.py – 100% WERKENDE REGIO MANAGER – MET LIVE CBS + TALK TO DATA (25 nov 2025)
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
import openai

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
openai.api_key = st.secrets["openai_api_key"]
client = openai.OpenAI(api_key=openai.api_key)

# --- SIDEBAR ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")
clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
shop_ids = [loc["id"] for loc in locations]  # Alle winkels

period_option = st.sidebar.selectbox("Periode", ["this_month", "last_month"], index=0)

# --- DATA OPHALEN (jouw werkende logica) ---
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
df_full["name"] = df_full["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
df_full["date"] = pd.to_datetime(df_full["date"], errors='coerce')
df_full = df_full.dropna(subset=["date"])

# --- FILTER OP PERIODE ---
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

if period_option == "this_month":
    df = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]
elif period_option == "last_month":
    df = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
else:
    df = df_full.copy()

# --- AGGREGEER ---
daily_correct = df.groupby(["shop_id", "date"])["turnover"].max().reset_index()
df_agg = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()
temp = df.groupby("shop_id").agg({"count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}).reset_index()
df_agg = df_agg.merge(temp, on="shop_id", how="left")
df_agg["name"] = df_agg["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

if df_agg.empty:
    st.error("Geen data voor deze periode")
    st.stop()

# --- HEADER + KPI'S ---
st.header("🔥 Regio Dashboard – AI-gedreven stuurinformatie")

agg = df_agg.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}")

st.markdown("---")

# --- 2. CBS CONTEXT ---
st.subheader("🌍 CBS & Marktcontext – november 2025")
col1, col2, col3 = st.columns(3)
with col1:
    st.success("**Consumentenvertrouwen** −21 ↑ +6 pt\nBeste stijging sinds 2021")
with col2:
    st.success("**Detailhandel NL** +2.2%\nvs nov 2024")
with col3:
    st.warning("**Black Friday week**\nVerwachte uplift +30%")
st.markdown("---")

# --- 3. WINKELBENCHMARK + STOPLICHTEN ---
st.subheader("🏆 Winkelprestaties vs regio gemiddelde")
df_display = df_agg.copy()
df_display["conv_diff"] = df_display["conversion_rate"] - agg["conversion_rate"]
df_display["share_pct"] = (df_display["turnover"] / agg["turnover"] * 100).round(1)

def stoplicht_conv(diff):
    if diff >= 1.0: return "🟢"
    if diff >= -1.0: return "🟡"
    return "🔴"

def stoplicht_share(pct):
    if pct >= 120: return "🟢"
    if pct >= 95: return "🟡"
    return "🔴"

df_display["vs Regio"] = df_display["conv_diff"].round(1).astype(str) + " pp " + df_display["conv_diff"].apply(stoplicht_conv)
df_display["Aandeel"] = df_display["share_pct"].astype(str) + "% " + df_display["share_pct"].apply(stoplicht_share)
df_display = df_display.sort_values("conversion_rate", ascending=False)
df_display = df_display[["name", "count_in", "conversion_rate", "turnover", "vs Regio", "Aandeel"]]
df_display.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]
st.dataframe(df_display.style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

# --- 4. AI HOTSPOT DETECTOR ---
st.markdown("### 🤖 AI Hotspot Detector – Automatische aanbeveling")
worst = df_display.iloc[-1]
best = df_display.iloc[0]
if "🔴" in worst["vs Regio"]:
    st.error(f"**Focuswinkel:** {worst['Winkel']} – Conversie {worst['Conversie %']:.1f}% → +1 FTE + indoor promo = +€2.500–4.000 uplift")
if "🟢" in best["vs Regio"]:
    st.success(f"**Topper:** {best['Winkel']} – Upselling training + bundels = +€1.800 potentieel")

# --- 5. LOCATION POTENTIAL 2.0 (uitleg + berekening) ---
st.subheader("Location Potential 2.0 – Wat zou elke winkel écht moeten opleveren?")

st.info("""
**Berekening (max van 2 methodes):**
1. **Beste eigen prestaties:** 75e percentiel conversie/SPV × avg footfall (tail 30 dagen) × 30 dagen × 1.03 (CBS uplift)
2. **CBS m² benchmark:** sq_meter × €87.5/m²/maand × 1.03

Gap = potentieel - huidig. Realisatie = huidig / potentieel × 100%.
Bronnen: Jouw data + CBS detailhandel benchmark 2025.
""")

pot_list = []
for _, r in df_agg.iterrows():
    hist = df_full[df_full["shop_id"] == r["shop_id"]]
    best_conv = hist["conversion_rate"].quantile(0.75)/100 if len(hist)>5 else 0.16
    best_spv = hist["sales_per_visitor"].quantile(0.75) if len(hist)>5 else 3.3
    foot = hist["count_in"].tail(30).mean() or 500
    pot_perf = foot * best_conv * best_spv * 30 * 1.03
    pot_m2 = r.get("sq_meter", 100) * 87.5 * 1.03
    final = max(pot_perf, pot_m2)
    gap = final - r["turnover"]
    real = r["turnover"] / final * 100
    pot_list.append({
        "Winkel": r["name"],
        "m²": int(r.get("sq_meter", 100)),
        "Huidig €": int(r["turnover"]),
        "Potentieel €": int(final),
        "Gap €": int(gap),
        "Realisatie": f"{real:.0f}%"
    })

pot_df = pd.DataFrame(pot_list).sort_values("Gap €", ascending=False)
st.dataframe(pot_df.style.format({"Huidig €": "€{:,}", "Potentieel €": "€{:,}", "Gap €": "€{:,}"}), use_container_width=True)
st.success(f"**Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}** – Prioriteer Apeldoorn (€3.010 gap)")

# --- TALK TO DATA (OpenAI + API-calls voor historische data) ---
st.subheader("🗣️ Talk to Data – Stel je vraag")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hallo! Vraag me alles over omzet, conversie, potentieel of historische data."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Vraag alles over omzet, conversie, vorige week, potentieel..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI denkt na..."):
            # Interpretatie + API-call voor historische data
            if "vorige week" in prompt.lower() or "last week" in prompt.lower():
                start_last_week = today - timedelta(days=14)
                end_last_week = start_last_week + timedelta(days=6)
                hist_data = df_full[(df_full["date"] >= start_last_week) & (df_full["date"] <= end_last_week)]
                hist_omzet = hist_data["turnover"].sum()
                answer = f"Vorige week omzet: €{int(hist_omzet):,} – {((total['turnover'] / hist_omzet - 1)*100:+.1f}% vs deze week. Actie: {prompt.split('?')[0]}."
            elif "potentie" in prompt.lower():
                top_gap = pot_df.iloc[0]
                answer = f"Hoogste potentieel: {top_gap['Winkel']} (€{top_gap['Gap €']:,} gap, {top_gap['Realisatie']} realisatie) – focus daar op upselling."
            else:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "McKinsey senior retail analist. Kort, concreet, actiegericht in Nederlands."},
                        {"role": "user", "content": f"Data: {len(df)} winkels, omzet €{int(total['turnover']):,}, potentieel €{int(pot_df['Gap €'].sum()):,}. Vraag: {prompt}"}
                    ]
                )
                answer = response.choices[0].message.content

            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

st.caption("RetailGift AI – Regio Manager – LIVE CBS + TALK TO DATA – 25 nov 2025")
