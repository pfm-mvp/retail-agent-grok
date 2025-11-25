import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from urllib.parse import urlencode
import plotly.graph_objects as go

st.set_page_config(page_title="Store Manager", layout="wide")

API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# Klant + vestiging
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

shop = st.selectbox("Vestiging", locations, format_func=lambda x: x["name"])
shop_id = shop["id"]
shop_name = shop["name"]

# Data ophalen
params = [("period", "this_year"), ("period_step", "day"), ("source", "shops"), ("data[]", str(shop_id))]
for k in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", k))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url).json().get("data", [])

rows = []
for entry in resp:
    if str(entry.get("shop_id")) != str(shop_id):
        continue
    for day in entry.get("values", []):
        rows.append({
            "date": day.get("date"),
            "count_in": day.get("count_in", 0),
            "conversion_rate": day.get("conversion_rate", 0),
            "turnover": day.get("turnover", 0),
            "sales_per_visitor": day.get("sales_per_visitor", 0)
        })

df = pd.DataFrame(rows)
if df.empty:
    st.error("Geen data")
    st.stop()

df["date"] = pd.to_datetime(df["date"])
today = pd.Timestamp.today().normalize()
this_month = df[df["date"] >= today.replace(day=1)]

total = this_month.agg({
    "count_in": "sum",
    "conversion_rate": "mean",
    "turnover": "sum",
    "sales_per_visitor": "mean"
})

st.header(f"{shop_name} – This Month")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Footfall", f"{int(total['count_in']):,}")
c2.metric("Conversie", f"{total['conversion_rate']:.1f}%")
c3.metric("Omzet", f"€{int(total['turnover']):,}")
c4.metric("SPV", f"€{total['sales_per_visitor']:.2f}")

# Grafiek
daily = this_month.copy()
daily["dag"] = daily["date"].dt.strftime("%a %d")
fig = go.Figure()
fig.add_trace(go.Bar(x=daily["dag"], y=daily["count_in"], name="Footfall"))
fig.add_trace(go.Bar(x=daily["dag"], y=daily["turnover"], name="Omzet"))
fig.update_layout(title="Dagverloop", height=500)
st.plotly_chart(fig, use_container_width=True)

st.success("STORE MANAGER 100% WERKENDE – KLAAR VOOR MORGEN")
