# pages/retailgift_regio.py – REGIO MANAGER MET LIVE CBS DATA (vertrouwen + detailhandel omzet)
import streamlit as st
import requests
import pandas as pd
from datetime import date
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Regio Manager", layout="wide")

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
CBS_KEY = st.secrets["cbs_api_key"]  # jouw key in secrets

# --- KLANT + ALLE WINKELS ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
shop_ids = [loc["id"] for loc in locations]

# --- DATA OPHALEN (jouw originele logica) ---
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover"]:
    params.append(("data_output[]", output))
url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()

# --- ROBUUSTE NORMALISATIE (jouw werkende versie) ---
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
            "turnover": float(day.get("turnover", 0) or 0)
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
@st.cache_data(ttl=86400)
def get_cbs_data():
    # Consumentenvertrouwen (maandelijks)
    url = "https://opendata.cbs.nl/ODataApi/OData/83693NED/TypedDataSet?$filter=Perioden ge '2025MM01'"
    vertrouwen = requests.get(url, headers={"Ocp-Apim-Subscription-Key": CBS_KEY}).json()
    vertrouwen_maand = {v["Perioden"][:7]: v["Consumentenvertrouwen_1"] for v in vertrouwen["value"]}

    # Detailhandel omzet (maandelijks)
    url = "https://opendata.cbs.nl/ODataApi/OData/85828NED/TypedDataSet?$filter=Perioden ge '2025MM01' and Branche eq 'Totaal detailhandel'"
    omzet = requests.get(url, headers={"Ocp-Apim-Subscription-Key": CBS_KEY}).json()
    omzet_maand = {v["Perioden"][:7]: v["OmzetIndex_3"] for v in omzet["value"]}

    return vertrouwen_maand, omzet_maand

vertrouwen, omzet_nl = get_cbs_data()

# --- GRAFIEK CBS + REGIO OMZET ---
st.subheader("Consumentenvertrouwen + Detailhandel NL vs Jouw regio")
monthly = df.groupby(df["date"].dt.strftime("%b"))["turnover"].sum().reindex(["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec"], fill_value=0)

fig = go.Figure()
fig.add_trace(go.Bar(x=monthly.index, y=monthly.values, name="Jouw regio omzet", marker_color="#ff7f0e"))
fig.add_trace(go.Scatter(x=list(vertrouwen.keys()), y=list(vertrouwen.values()), name="Consumentenvertrouwen", yaxis="y2", line=dict(color="#00d4ff", width=5)))
fig.add_trace(go.Scatter(x=list(omzet_nl.keys()), y=list(omzet_nl.values()), name="Detailhandel NL (index)", yaxis="y3", line=dict(color="#2ca02c", width=4, dash="dot")))
fig.update_layout(
    title="Live CBS data vs jouw regio",
    yaxis=dict(title="Omzet €"),
    yaxis2=dict(title="Vertrouwen", overlaying="y", side="right"),
    yaxis3=dict(title="NL omzet index", overlaying="y", side="right", position=0.94),
    height=500
)
st.plotly_chart(fig, use_container_width=True)

st.success("REGIO MANAGER MET LIVE CBS DATA – KLAAR VOOR MORGEN")
st.balloons()
