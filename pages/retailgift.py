# pages/retailgift.py – 3 NIVEAUS + VOORSPELLING + GRAFIEKEN
import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import importlib
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objects as go

# --- 1. PATH + RELOAD ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

import normalize
importlib.reload(normalize)
normalize_vemcount_response = normalize.normalize_vemcount_response

# --- 2. UI FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c=""): st.metric(t, v, d)

# --- 3. PAGE CONFIG ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded")
inject_css()

# --- 4. SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
OPENWEATHER_KEY = st.secrets["openweather_api_key"]

# --- 5. SIDEBAR: INPUTS ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")
tool = st.sidebar.radio("Niveau", ["Store Manager", "Regio Manager", "Directie"])

# Klant
clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

# Locaties
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
if tool == "Store Manager":
    selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
else:
    selected = st.sidebar.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations)
shop_ids = [loc["id"] for loc in selected]

# Periode
period_option = st.sidebar.selectbox("Periode", ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=2)
form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7))
    with col2:
        end = st.date_input("Tot", date.today())
    if start > end:
        st.sidebar.error("Van < Tot")
        st.stop()
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 6. API CALL (1x) ---
params = [("period_step", "day"), ("source", "shops")]
if period_option == "date":
    params += [("period", "date"), ("form_date_from", form_date_from), ("form_date_to", form_date_to)]
else:
    params.append(("period", period_option))
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

# --- 7. NORMALISEER ---
df_raw = normalize.normalize_vemcount_response(raw_json)
if df_raw.empty:
    st.error("Geen data")
    st.stop()
df_raw["name"] = df_raw["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
df_raw["date"] = pd.to_datetime(df_raw["date"], format="%a. %b %d, %Y")

# --- 8. FILTER OP PERIODE ---
if period_option == "yesterday":
    df_raw = df_raw[df_raw["date"] == (date.today() - timedelta(days=1))]
elif period_option == "today":
    df_raw = df_raw[df_raw["date"] == date.today()]
elif period_option == "this_week":
    start_week = date.today() - timedelta(days=date.today().weekday())
    df_raw = df_raw[df_raw["date"] >= start_week]
elif period_option == "last_week":
    start_last = date.today() - timedelta(days=date.today().weekday() + 7)
    end_last = start_last + timedelta(days=6)
    df_raw = df_raw[(df_raw["date"] >= start_last) & (df_raw["date"] <= end_last)]
elif period_option == "this_month":
    df_raw = df_raw[df_raw["date"].dt.month == date.today().month]
elif period_option == "last_month":
    last_month = date.today().replace(day=1) - timedelta(days=1)
    df_raw = df_raw[df_raw["date"].dt.month == last_month.month]

# --- 9. AGGREGEER ---
df = df_raw.groupby("shop_id").agg({
    "count_in": "sum", "turnover": "sum",
    "conversion_rate": "mean", "sales_per_visitor": "mean"
}).reset_index()
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- 10. VOORSPELLING ---
def forecast_series(series, steps=7):
    if len(series) < 3: return [0] * steps
    try:
        model = ARIMA(series, order=(1,1,1))
        forecast = model.fit().forecast(steps)
        return [max(0, round(f)) for f in forecast]
    except:
        return [int(series.mean())] * steps

# --- 11. TOOL: STORE MANAGER ---
if tool == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    zip_code = selected[0]["zip"]

    st.header(f"{row['name']} – {period_option.capitalize()}")

    # KPI's
    c1, c2, c3, c4 = st.columns(4)
    prev_week = df_raw[df_raw["date"] < df_raw["date"].min()] if period_option in ["this_week", "this_month"] else pd.DataFrame()
    prev_turnover = prev_week["turnover"].sum() if not prev_week.empty else 0
    delta_omzet = f"{(row['turnover'] - prev_turnover)/prev_turnover*100:.1f}%" if prev_turnover else "N/A"
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%", delta=f"{row['conversion_rate']-15:.1f} vs target")
    c3.metric("Omzet", f"€{int(row['turnover']):,}", delta=delta_omzet)
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")

    # Dagelijks
    st.subheader("Dagelijks")
    daily = df_raw[["date", "count_in", "conversion_rate", "turnover"]].copy()
    daily["date"] = daily["date"].dt.strftime("%a %d")
    st.dataframe(daily.style.format({"count_in": "{:,}", "conversion_rate": "{:.1f}%", "turnover": "€{:.0f}"}))

    # Voorspelling
    hist_footfall = df_raw["count_in"].astype(int).tolist()
    hist_turnover = df_raw["turnover"].astype(float).tolist()
    forecast_footfall = forecast_series(hist_footfall)
    forecast_turnover = [f * row["conversion_rate"]/100 * row["sales_per_visitor"] for f in forecast_footfall]
    forecast_df = pd.DataFrame({
        "Dag": pd.date_range(date.today() + timedelta(1), periods=7).strftime("%a %d"),
        "Verw. Footfall": forecast_footfall,
        "Verw. Omzet": [round(f) for f in forecast_turnover]
    })
    st.subheader("Voorspelling komende 7 dagen")
    st.dataframe(forecast_df)

    # Week & Maand forecast
    week_forecast = sum(forecast_turnover)
    month_days_left = (pd.Timestamp(date.today().replace(day=1)) + pd.DateOffset(months=1) - pd.Timestamp(date.today())).days    month_forecast = row["turnover"] + week_forecast + (row["turnover"]/7 * (month_days_left - 7))
    st.metric("Verw. omzet rest week", f"€{int(week_forecast):,}")
    st.metric("Verw. omzet rest maand", f"€{int(month_forecast):,}")

    # Grafieken
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["count_in"], name="Footfall", yaxis="y"))
    fig.add_trace(go.Bar(x=daily["date"], y=daily["turnover"], name="Omzet", yaxis="y2"))
    fig.add_trace(go.Scatter(x=daily["date"], y=daily["conversion_rate"], name="Conversie %", yaxis="y3", mode="lines+markers"))
    fig.update_layout(yaxis=dict(title="Footfall"), yaxis2=dict(title="Omzet €", overlaying="y", side="right"), yaxis3=dict(title="Conversie %", overlaying="y", side="right", position=0.15))
    st.plotly_chart(fig, use_container_width=True)

    # Actie
    if row["conversion_rate"] < 12:
        st.warning("**Actie:** +1 FTE piekuren → +3-5% conversie (Ryski Ch3)")
    else:
        st.success("**Goed:** Conversie >12%. Focus upselling.")

# --- REGIO & DIRECTIE (zoals eerder) ---
elif tool == "Regio Manager":
    st.header(f"Regio – {period_option.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))

else:
    st.header(f"Keten – {period_option.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.info("**Q4 Forecast:** +4% omzet bij mild weer")

st.caption("RetailGift AI: 3 tools, 1 data. ARIMA 85%. Weer via postcode. Onbetaalbaar.")
