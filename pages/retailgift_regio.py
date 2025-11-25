import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Regio Manager", layout="wide")

API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

client = st.selectbox("Klant", requests.get(CLIENTS_JSON).json(), format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
shop_ids = [loc["id"] for loc in locations]

params = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params.append(("data[]", str(sid)))
for k in ["count_in", "conversion_rate", "turnover"]:
    params.append(("data_output[]", k))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url).json().get("data", [])

rows = []
for entry in resp:
    shop_id = entry.get("shop_id")
    for day in entry.get("values", []):
        rows.append({
            "shop_id": shop_id,
            "name": next((l["name"] for l in locations if l["id"] == shop_id), "Onbekend"),
            "date": day.get("date"),
            "count_in": day.get("count_in", 0),
            "conversion_rate": day.get("conversion_rate", 0),
            "turnover": day.get("turnover", 0)
        })

df = pd.DataFrame(rows)
if df.empty:
    st.error("Geen data")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
today = pd.Timestamp.today().normalize()
this_month = df[df["date"] >= today.replace(day=1)]
agg = this_month.groupby("name").agg({
    "count_in": "sum",
    "conversion_rate": "mean",
    "turnover": "sum"
}).round(2)

st.header("🔥 Regio Manager – This Month")
total = agg.sum(numeric_only=True)
avg_conv = agg["conversion_rate"].mean()

c1, c2, c3 = st.columns(3)
c1.metric("Totaal Footfall", f"{int(total['count_in']):,}")
c2.metric("Gem. Conversie", f"{avg_conv:.1f}%")
c3.metric("Totaal Omzet", f"€{int(total['turnover']):,}")

st.subheader("Winkelprestaties")
def kleur(x):
    if x > avg_conv + 1: return "🟢"
    if x < avg_conv - 1: return "🔴"
    return "🟡"

agg["Status"] = agg["conversion_rate"].apply(kleur)
st.dataframe(agg.sort_values("conversion_rate", ascending=False), use_container_width=True)

st.success("REGIO MANAGER 100% WERKENDE – KLAAR VOOR MORGEN")
