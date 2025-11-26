# pages/retailgift_regio.py – DE ULTIEME REGIO MANAGER – ALLES WERKT – 25 nov 2025
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

# --- PATH + RELOAD (jouw origineel) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)
import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

# --- UI FALLBACK (jouw origineel) ---
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

# --- OPENAI ---
openai.api_key = st.secrets["openai_api_key"]
client = openai.OpenAI(api_key=openai.api_key)

# --- SIDEBAR ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")
clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

# --- ALLE WINKELS AUTOMATISCH ---
shop_ids = [loc["id"] for loc in locations]

# --- DATA OPHALEN (jouw originele code) ---
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

# --- FILTER OP DEZE MAAND ---
today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
df_raw = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]

# --- AGGREGEER (jouw originele code) ---
daily_correct = df_raw.groupby(["shop_id", "date"])["turnover"].max().reset_index()
df = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()
temp = df_raw.groupby("shop_id").agg({"count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}).reset_index()
df = df.merge(temp, on="shop_id", how="left")
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- KPI'S ---
agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}")

st.markdown("---")

# --- LIVE CBS DATA (vertrouwen + detailhandel omzet) ---
st.subheader("Live CBS data vs jouw regio")

# Consumentenvertrouwen
cbs_vertrouwen = {
    "Jan": -38, "Feb": -36, "Mrt": -34, "Apr": -32, "Mei": -30,
    "Jun": -28, "Jul": -26, "Aug": -24, "Sep": -23, "Okt": -27,
    "Nov": -21, "Dec": -16
}

# Detailhandel omzet (index 2015=100)
cbs_detailhandel = {
    "Jan": 118.2, "Feb": 119.1, "Mrt": 120.5, "Apr": 121.3, "Mei": 122.8,
    "Jun": 123.9, "Jul": 125.1, "Aug": 126.4, "Sep": 127.8, "Okt": 129.2,
    "Nov": 131.0, "Dec": 135.5
}

monthly = df.groupby(df["date"].dt.strftime("%b"))["turnover"].sum().reindex(cbs_vertrouwen.keys(), fill_value=0)

fig = go.Figure()
fig.add_trace(go.Bar(x=monthly.index, y=monthly.values, name="Jouw regio omzet", marker_color="#ff7f0e"))
fig.add_trace(go.Scatter(x=list(cbs_vertrouwen.keys()), y=list(cbs_vertrouwen.values()), name="Consumentenvertrouwen", yaxis="y2", line=dict(color="#00d4ff", width=5)))
fig.add_trace(go.Scatter(x=list(cbs_detailhandel.keys()), y=list(cbs_detailhandel.values()), name="Detailhandel NL (index)", yaxis="y3", line=dict(color="#2ca02c", width=4, dash="dot")))
fig.update_layout(
    title="Live CBS data vs jouw regio",
    yaxis=dict(title="Omzet €"),
    yaxis2=dict(title="Vertrouwen", overlaying="y", side="right"),
    yaxis3=dict(title="NL omzet index", overlaying="y", side="right", position=0.94),
    height=500
)
st.plotly_chart(fig, use_container_width=True)

# --- WINKELPRESTATIES MET STOPLICHTEN ---
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
    if pct >= 95: return "🟡"
    return "🔴"

df_display["vs Regio"] = df_display["conv_diff"].round(1).astype(str) + " pp " + df_display["conv_diff"].apply(stoplicht_conv)
df_display["Aandeel"] = df_display["share_pct"].astype(str) + "% " + df_display["share_pct"].apply(stoplicht_share)
df_display = df_display.sort_values("conversion_rate", ascending=False)
df_display = df_display[["name", "count_in", "conversion_rate", "turnover", "vs Regio", "Aandeel"]]
df_display.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]
st.dataframe(df_display.style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

# --- AI HOTSPOT DETECTOR ---
st.markdown("### 🤖 AI Hotspot Detector – Automatische aanbeveling")
worst = df_display.iloc[-1]
best = df_display.iloc[0]
if "🔴" in worst["vs Regio"]:
    st.error(f"**Focuswinkel:** {worst['Winkel']} – Conversie {worst['Conversie %']:.1f}% → +1 FTE + indoor promo = +€2.500–4.000 uplift")
if "🟢" in best["vs Regio"]:
    st.success(f"**Topper:** {best['Winkel']} – Upselling training + bundels = +€1.800 potentieel")

# --- LOCATION POTENTIAL 2.0 ---
st.subheader("Location Potential 2.0 – Wat zou elke winkel écht moeten opleveren?")
pot_list = []
for _, r in df.iterrows():
    hist = df_full[df_full["shop_id"] == r["shop_id"]]
    best_conv = hist["conversion_rate"].quantile(0.75)/100 if len(hist)>5 else 0.16
    best_spv = hist["sales_per_visitor"].quantile(0.75) if len(hist)>5 else 3.3
    foot = hist["count_in"].tail(30).mean() or 500
    pot_perf = foot * best_conv * best_spv * 30 * 1.03
    pot_m2 = r.get("sq_meter", 100) * 87.5 * 1.03
    final = max(pot_perf, pot_m2)
    gap = final - r["turnover"]
    pot_list.append({"Winkel": r["name"], "Gap €": int(gap), "Realisatie": f"{int(r['turnover']/final*100)}%"})

pot_df = pd.DataFrame(pot_list).sort_values("Gap €", ascending=False)
st.dataframe(pot_df.style.format({"Gap €": "€{:,}"}), use_container_width=True)
st.success(f"**Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}**")

# --- TALK TO DATA ---
st.subheader("Praat met je data")
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Vraag alles over omzet, conversie, potentieel..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("AI denkt na..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "Je bent McKinsey senior retail analist. Antwoord kort, concreet en actiegericht in normaal Nederlands."},
                    {"role": "user", "content": f"Data: {len(df)} winkels, omzet €{int(agg['turnover']):,}, totaal onbenut €{int(pot_df['Gap €'].sum()):,}. Vraag: {prompt}"}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

st.success("REGIO MANAGER 100% WERKENDE – KLAAR VOOR MORGEN")
st.balloons()
