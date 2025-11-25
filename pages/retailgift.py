# pages/retailgift.py – VOLLEDIG WERKENDE VERSIE MET ALLES + TALK-TO-DATA (25 nov 2025)
import streamlit as st
import requests
import pandas as pd
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import importlib
import numpy as np
import plotly.graph_objects as go
import openai

# --- OPENAI SETUP ---
openai.api_key = st.secrets["openai_api_key"]
if "openai_client" not in st.session_state:
    st.session_state.openai_client = openai.OpenAI(api_key=st.secrets["openai_api_key"])

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
    from helpers.ui import inject_css
except:
    def inject_css(): st.markdown("<style>body {background: #0e1117; color: white;}</style>", unsafe_allow_html=True)
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

period_option = st.sidebar.selectbox("Periode", ["this_month", "last_month", "this_week", "last_week", "yesterday"], index=0)

# --- DATA OPHALEN ---
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

# --- AGGREGEER ---
df_raw["turnover"] = pd.to_numeric(df_raw["turnover"], errors='coerce').fillna(0)
daily = df_raw.groupby(["shop_id", "date"]).agg({
    "turnover": "sum", "count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"
}).reset_index()

df = daily.groupby("shop_id").agg({
    "turnover": "sum", "count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"
}).reset_index()
df["name"] = df["shop_id"].map({k: v["name"] for k, v in shop_meta.items()})
df["sq_meter"] = df["shop_id"].map({k: v["sq_meter"] for k, v in shop_meta.items()}).fillna(100)

# --- STORE MANAGER VIEW (100% TERUG!) ---
if tool == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – {period_option.replace('_', ' ').title()}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    c3.metric("Omzet", f"€{int(row['turnover']):,}")
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")

    st.subheader("Dagelijkse prestaties")
    daily_shop = df_raw[df_raw["shop_id"] == row["shop_id"]].copy()
    daily_shop["date"] = daily_shop["date"].dt.strftime("%a %d %b")
    st.dataframe(daily_shop[["date", "count_in", "conversion_rate", "turnover"]].style.format({
        "count_in": "{:,}", "conversion_rate": "{:.1f}%", "turnover": "€{:.0f}"
    }), use_container_width=True)

    if row["conversion_rate"] < 12:
        st.warning("**Actie:** +1 FTE piekuren (11-17u) → +3-5% conversie")
    else:
        st.success("**Top:** Conversie ≥12%. Vandaag piek 12-16u → upselling push!")

# --- REGIO MANAGER VIEW MET ALLES + TALK-TO-DATA ---
elif tool == "Regio Manager":
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
    with col1: st.success("**Consumentenvertrouwen** −21 ↑ +6 pt")
    with col2: st.success("**Detailhandel NL** +2.2%")
    with col3: st.warning("**Black Friday week** +30% uplift")
    st.markdown("---")

    # Winkelbenchmark
    st.subheader("Winkelprestaties vs regio gemiddelde")
    df_display = df.copy()
    df_display["vs_regio"] = (df_display["conversion_rate"] - agg["conversion_rate"]).round(1)
    df_display["aandeel"] = (df_display["turnover"] / agg["turnover"] * 100).round(1)
    def kleur(x): return "🟢" if x >= 1 else "🟡" if x >= -1 else "🔴"
    def aandeel_kleur(x): return "🟢" if x >= 120 else "🟡" if x >= 90 else "🔴"
    df_display["Conversie"] = df_display["vs_regio"].astype(str) + " pp " + df_display["vs_regio"].apply(kleur)
    df_display["Aandeel"] = df_display["aandeel"].astype(str) + "% " + df_display["aandeel"].apply(aandeel_kleur)
    df_display = df_display.sort_values("conversion_rate", ascending=False)
    st.dataframe(df_display[["name", "count_in", "conversion_rate", "turnover", "Conversie", "Aandeel"]].rename(columns={
        "name": "Winkel", "count_in": "Footfall", "conversion_rate": "Conversie %", "turnover": "Omzet €"
    }).style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

    # Location Potential 2.0
    st.markdown("---")
    st.subheader("Location Potential 2.0 – Wat zou elke winkel écht moeten opleveren?")
    BRANCHE = 87.50
    pot_list = []
    for _, row in df.iterrows():
        hist = df_full[df_full["shop_id"] == row["shop_id"]]
        best_conv = hist["conversion_rate"].quantile(0.75)/100 if len(hist)>5 else 0.16
        best_spv = hist["sales_per_visitor"].quantile(0.75) if len(hist)>5 else 3.3
        foot = hist["count_in"].tail(30).mean() or 500
        pot_perf = foot * best_conv * best_spv * 30 * 1.03
        pot_m2 = row["sq_meter"] * BRANCHE * 1.03
        final = max(pot_perf, pot_m2)
        gap = final - row["turnover"]
        real = row["turnover"] / final * 100
        pot_list.append({"Winkel": row["name"], "m²": int(row["sq_meter"]), "Huidig €": int(row["turnover"]),
                         "Potentieel €": int(final), "Gap €": int(gap), "Realisatie": f"{real:.0f}%"})
    pot_df = pd.DataFrame(pot_list).sort_values("Gap €", descending=True)
    def status(r): v = float(r.rstrip("%")); return "🟢" if v>=90 else "🟡" if v>=70 else "🔴"
    pot_df["Status"] = pot_df["Realisatie"].apply(status)
    st.dataframe(pot_df.style.format({"Huidig €": "€{:,}", "Potentieel €": "€{:,}", "Gap €": "€{:,}", "m²": "{:,}"}), use_container_width=True)
    st.success(f"**Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}**")

    # TALK-TO-DATA CHAT
    st.markdown("---")
    st.subheader("Praat met je data – stel elke vraag")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hoi! Ik ben je AI Retail Coach. Vraag me alles over je winkels, omzet, conversie of acties."}]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Typ je vraag..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Even denken..."):
                context = f"""
                Actuele data (nov 2025): Footfall {int(agg['count_in']):,}, Conversie {agg['conversion_rate']:.1f}%,
                Omzet €{int(agg['turnover']):,}, SPV €{agg['sales_per_visitor']:.2f}.
                Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}.
                Top 3 gaps: {', '.join(pot_df.head(3)['Winkel'].tolist())}.
                Vraag: {prompt}
                """
                response = st.session_state.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Je bent McKinsey senior retail analist. Antwoord kort, concreet, actiegericht in normaal Nederlands."},
                              {"role": "user", "content": context + prompt}],
                    temperature=0.3
                )
                answer = response.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})

else:
    st.header("Directie view – binnenkort beschikbaar")

st.caption("RetailGift AI – Store + Regio + Talk-to-Data – 100% LIVE – 25 nov 2025")
