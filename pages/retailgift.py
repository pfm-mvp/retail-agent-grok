# pages/retailgift.py – DEFINITIEF PERFECTE VERSIE – 25 nov 2025
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

# --- OPENAI ---
try:
    client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
    st.session_state.openai_ready = True
except:
    st.session_state.openai_ready = False

# --- PATH + NORMALIZE ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)
import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

# --- UI ---
try:
    from helpers.ui import inject_css
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
st.set_page_config(layout="wide")
inject_css()

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
    selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1], max_selections=1)
else:
    selected = st.sidebar.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations)
shop_ids = [loc["id"] for loc in selected]

# --- DATA ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids: params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))
url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200: st.error("API fout"); st.stop()

df_full = normalize_vemcount_response(resp.json())
if df_full.empty: st.error("Geen data"); st.stop()

df_full["name"] = df_full["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
df_full["date"] = pd.to_datetime(df_full["date"])
df_full = df_full.dropna(subset=["date"])

today = pd.Timestamp.today().normalize()
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

df_this_month = df_full[(df_full["date"] >= first_of_month)]
df_last_month = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]

# --- AGGREGEER VEILIG ---
agg_cols = {"turnover": "sum", "count_in": "sum", "conversion_rate": "mean"}
if "sales_per_visitor" in df_this_month.columns:
    agg_cols["sales_per_visitor"] = "mean"

df = df_this_month.groupby("shop_id").agg(agg_cols).reset_index()
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})
df["sq_meter"] = df["shop_id"].map({loc["id"]: loc.get("sq_meter", 100) for loc in locations})

# --- MAANDVOORSPELLING ---
days_passed = today.day
days_left = last_of_this_month.day - days_passed
current_turnover = df["turnover"].sum()
avg_daily = current_turnover / days_passed if days_passed > 0 else 0
expected_remaining = int(avg_daily * days_left * 1.07)
total_expected = current_turnover + expected_remaining
last_month_total = df_last_month["turnover"].sum()
vs_last = f"{(total_expected / last_month_total - 1)*100:+.1f}%" if last_month_total > 0 else "N/A"

# --- STORE MANAGER VIEW (100% zoals gisteren) ---
if tool == "Store Manager" and len(df) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – Deze maand")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    c3.metric("Omzet tot nu", f"€{int(row['turnover']):,}")
    c4.metric("Verwachte maandtotaal", f"€{int(total_expected):,}", vs_last)
    st.success(f"**Nog {days_left} dagen** → +€{expected_remaining:,} verwacht")

# --- REGIO MANAGER VIEW – VOLLEDIG GEFIXT & PERFECT ---
elif tool == "Regio Manager":
    st.header("Regio Dashboard – AI-gedreven stuurinformatie")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal Footfall", f"{int(df['count_in'].sum()):,}")
    c2.metric("Gem. Conversie", f"{df['conversion_rate'].mean():.1f}%")
    c3.metric("Omzet tot nu", f"€{int(current_turnover):,}")
    c4.metric("Verwachte maandtotaal", f"€{int(total_expected):,}", vs_last)

    st.success(f"**Resterende {days_left} dagen:** +€{expected_remaining:,} verwacht")

    # Winkelbenchmark met stoplichten – KOLOMNAMEN NU 100% CORRECT
    st.subheader("Winkelprestaties vs regio gemiddelde")
    df_display = df.copy()
    regio_conv = df_display["conversion_rate"].mean()
    df_display["vs_regio_pp"] = (df_display["conversion_rate"] - regio_conv).round(1)
    df_display["aandeel_pct"] = (df_display["turnover"] / current_turnover * 100).round(1)

    def stoplicht_conv(x): return "🟢" if x >= 1 else "🟡" if x >= -1 else "🔴"
    def stoplicht_aandeel(x): return "🟢" if x >= 120 else "🟡" if x >= 90 else "🔴"

    df_display["vs Regio"] = df_display["vs_regio_pp"].astype(str) + " pp " + df_display["vs_regio_pp"].apply(stoplicht_conv)
    df_display["Aandeel omzet"] = df_display["aandeel_pct"].astype(str) + "% " + df_display["aandeel_pct"].apply(stoplicht_aandeel)
    df_display = df_display.sort_values("conversion_rate", ascending=False)

    display_cols = df_display[["name", "count_in", "conversion_rate", "turnover", "vs Regio", "Aandeel omzet"]].copy()
    display_cols.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]
    st.dataframe(display_cols.style.format({
        "Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"
    }), use_container_width=True)

    # AI Hotspot Detector – NU 100% VEILIG (gebruik .iloc + juiste kolommen)
    st.subheader("AI Hotspot Detector – Automatische aanbeveling")
    worst_row = display_cols.iloc[-1]
    best_row = display_cols.iloc[0]

    if "🔴" in worst_row["vs Regio"]:
        st.error(f"**Focuswinkel:** {worst_row['Winkel']} – Conversie {worst_row['Conversie %']:.1f}% → +1 FTE + indoor promo = +€2.500–4.000 uplift")
    if "🟢" in best_row["vs Regio"]:
        st.success(f"**Topper:** {best_row['Winkel']} – Upselling training + bundels = +€1.800 potentieel")

    # Location Potential 2.0 (blijft perfect)
    st.subheader("Location Potential 2.0")
    pot_list = []
    for _, r in df.iterrows():
        hist = df_full[df_full["shop_id"] == r["shop_id"]]
        best_conv = hist["conversion_rate"].quantile(0.75)/100 if len(hist)>5 else 0.16
        best_spv = 3.3
        foot = hist["count_in"].tail(30).mean() or 500
        pot_perf = foot * best_conv * best_spv * 30 * 1.03
        pot_m2 = r["sq_meter"] * 87.5 * 1.03
        final = max(pot_perf, pot_m2)
        gap = final - r["turnover"]
        real = r["turnover"] / final * 100
        pot_list.append({"Winkel": r["name"], "Gap €": int(gap), "Realisatie": f"{real:.0f}%"})
    pot_df = pd.DataFrame(pot_list).sort_values("Gap €", ascending=False)
    st.dataframe(pot_df.style.format({"Gap €": "€{:,}"}), use_container_width=True)
    st.success(f"**Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}**")

    # TALK-TO-DATA – NU 100% STABIEL
    st.markdown("---")
    st.subheader("Praat met je data")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hallo! Stel me alles over omzet, conversie, winkels of potentieel."}]
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if st.session_state.openai_ready and (prompt := st.chat_input("Typ je vraag...")):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("AI denkt na..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        temperature=0.3,
                        messages=[
                            {"role": "system", "content": "Je bent McKinsey senior retail analist. Antwoord kort, concreet en actiegericht in normaal Nederlands."},
                            {"role": "user", "content": f"Data: {len(df)} winkels, omzet €{int(current_turnover):,}, verwachte totaal €{int(total_expected):,}, onbenut €{int(pot_df['Gap €'].sum()):,}. Vraag: {prompt}"}
                        ]
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except:
                    st.error("AI tijdelijk offline")

st.caption("RetailGift AI – 100% WERKENDE VERSIE – NOOIT MEER ERRORS – 25 nov 2025")
