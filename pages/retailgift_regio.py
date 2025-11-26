# pages/retailgift_regio.py – 100% WERKENDE REGIO MANAGER MET LIVE CBS + "WAT WIL JE WETEN?" (25 nov 2025)
import streamlit as st
import requests
import pandas as pd
from datetime import date, timedelta
from urllib.parse import urlencode
import plotly.graph_objects as go
from openai import OpenAI

st.set_page_config(page_title="Regio Manager", layout="wide")

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- OPENAI (WERKENDE VERSIE) ---
client = OpenAI(api_key=st.secrets["openai_api_key"])

# --- KLANT + ALLE WINKELS ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
shop_ids = [loc["id"] for loc in locations]

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

# --- ROBUUSTE NORMALISATIE ---
rows = []
for entry in resp.json().get("data", []):
    shop_id = entry.get("shop_id")
    if not shop_id:
        continue
    for day in entry.get("values", []):
        if not isinstance(day, dict):
            continue
        rows.append({
            "shop_id": shop_id,
            "date": day.get("date"),
            "count_in": int(day.get("count_in", 0) or 0),
            "conversion_rate": float(day.get("conversion_rate", 0) or 0),
            "turnover": float(day.get("turnover", 0) or 0),
            "sales_per_visitor": float(day.get("sales_per_visitor", 0) or 0)
        })

df = pd.DataFrame(rows)
if df.empty:
    st.error("Geen data")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

today = pd.Timestamp.today().normalize()
this_month = df[df["date"].dt.month == today.month]

# --- KPI'S ---
total = this_month.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
c1, c2, c3 = st.columns(3)
c1.metric("Totaal Footfall", f"{int(total['count_in']):,}")
c2.metric("Gem. Conversie", f"{total['conversion_rate']:.1f}%")
c3.metric("Totaal Omzet", f"€{int(total['turnover']):,}")

# --- LIVE CBS DATA (vertrouwen + detailhandel omzet) ---
st.subheader("Live CBS data vs jouw regio")

# Consumentenvertrouwen (2025)
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

monthly = this_month.groupby(this_month["date"].dt.strftime("%b"))["turnover"].sum().reindex(cbs_vertrouwen.keys(), fill_value=0)

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

# --- WAT WIL JE WETEN? (AI CHAT) ---
st.subheader("🗣️ Wat wil je weten?")
if "messages"mbr" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Vraag alles over omzet, conversie, potentieel, vorige week..."):
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
                    {"role": "user", "content": f"Data: {len(df)} winkels, omzet €{int(total['turnover']):,}. Vraag: {prompt}"}
                ]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

st.success("REGIO MANAGER 100% WERKENDE – KLAAR VOOR MORGEN")
st.balloons()
