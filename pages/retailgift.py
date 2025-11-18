# pages/retailgift.py – STORE MANAGER VOLLEDIG WERKENDE VERSIE
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from urllib.parse import urlencode
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objects as go

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- SIDEBAR ---
st.sidebar.image("https://i.imgur.com/8Y5fX5P.png", width=200)
st.sidebar.title("STORE TRAFFIC IS A GIFT")

clients = requests.get(CLIENTS_JSON).json()
client = st.sidebar.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]

locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.sidebar.multiselect("Vestiging", locations, format_func=lambda x: x["name"], default=locations[:1])
shop_ids = [loc["id"] for loc in selected]

period_option = st.sidebar.selectbox("Periode", 
    ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=3)

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

# --- DATA OPHALEN (this_year) ---
params = [
    ("period", "this_year"), ("period_step", "day"), ("source", "shops")
]
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

url = f"{API_BASE}/get-report?{urlencode(params, doseq=True, safe='[]')}"
resp = requests.get(url)
if resp.status_code != 200:
    st.error("API fout")
    st.stop()

# --- NORMALISEER ---
def normalize_data(raw_json):
    data = []
    for shop in raw_json.get("data", []):
        shop_id = shop["shop_id"]
        for day in shop.get("days", []):
            row = {"shop_id": shop_id, "date": day["date"]}
            for k, v in day.items():
                if k != "date":
                    row[k] = float(v) if v not in ["", None] else 0.0
            data.append(row)
    return pd.DataFrame(data)

df_full = normalize_data(resp.json())
if df_full.empty:
    st.error("Geen data beschikbaar")
    st.stop()

df_full["date"] = pd.to_datetime(df_full["date"])
df_full["name"] = df_full["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- DATUMVARIABELEN ---
today = pd.Timestamp.today().normalize()
start_week = today - pd.Timedelta(days=today.weekday())
end_week = start_week + pd.Timedelta(days=6)
start_last_week = start_week - pd.Timedelta(days=7)
end_last_week = end_week - pd.Timedelta(days=7)
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

# --- FILTER OP PERIODE ---
if period_option == "yesterday":
    df_raw = df_full[df_full["date"] == (today - pd.Timedelta(days=1))]
elif period_option == "today":
    df_raw = df_full[df_full["date"] == today]
elif period_option == "this_week":
    df_raw = df_full[(df_full["date"] >= start_week) & (df_full["date"] <= end_week)]
elif period_option == "last_week":
    df_raw = df_full[(df_full["date"] >= start_last_week) & (df_full["date"] <= end_last_week)]
elif period_option == "this_month":
    df_raw = df_full[(df_full["date"] >= first_of_month) & (df_full["date"] <= last_of_this_month)]
elif period_option == "last_month":
    df_raw = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
elif period_option == "date":
    start = pd.to_datetime(form_date_from)
    end = pd.to_datetime(form_date_to)
    df_raw = df_full[(df_full["date"] >= start) & (df_full["date"] <= end)]
else:
    df_raw = df_full.copy()

# --- VORIGE PERIODE (op volledige data) ---
prev_start = prev_end = None
if period_option == "last_week":
    prev_start = start_last_week - pd.Timedelta(days=7)
    prev_end = end_last_week - pd.Timedelta(days=7)
elif period_option == "this_week":
    prev_start = start_last_week
    prev_end = end_last_week
elif period_option == "this_month":
    prev_start = first_of_last_month
    prev_end = first_of_month - pd.Timedelta(days=1)
elif period_option == "last_month":
    prev_start = first_of_last_month - pd.DateOffset(months=1)
    prev_end = first_of_last_month - pd.Timedelta(days=1)
elif period_option == "date":
    length = (pd.to_datetime(form_date_to) - pd.to_datetime(form_date_from)).days + 1
    prev_start = pd.to_datetime(form_date_from) - pd.Timedelta(days=length)
    prev_end = pd.to_datetime(form_date_from) - pd.Timedelta(days=1)

prev_agg = pd.Series({"count_in": 0, "turnover": 0, "conversion_rate": 0, "sales_per_visitor": 0})
if prev_start and prev_end:
    prev_data = df_full[(df_full["date"] >= prev_start) & (df_full["date"] <= prev_end)]
    if not prev_data.empty:
        prev_agg = prev_data[["count_in", "turnover", "conversion_rate", "sales_per_visitor"]].mean()

# --- AGGREGEER HUIDIGE PERIODE ---
df = df_raw.groupby("shop_id").agg({
    "count_in": "sum", "turnover": "sum",
    "conversion_rate": "mean", "sales_per_visitor": "mean"
}).reset_index()

# --- WEEKDAG-GEMIDDELDEN (ROBUST) ---
weekday_df = df_full.copy()
weekday_df["weekday"] = weekday_df["date"].dt.weekday
for col in ["conversion_rate", "sales_per_transaction"]:
    if col not in weekday_df.columns:
        weekday_df[col] = 0.0
weekday_avg = weekday_df.groupby("weekday")[["conversion_rate", "sales_per_transaction"]].mean()
weekday_avg = weekday_avg.reindex(range(7), fill_value=weekday_avg.mean() if not weekday_avg.empty else pd.Series({"conversion_rate": 0.12, "sales_per_transaction": 18.0}))

# --- VOORSPELLING FUNCTIE ---
def forecast_series(series, steps=7):
    series = [int(x) for x in series if pd.notna(x)]
    if len(series) == 0:
        return [0] * steps
    if len(series) < 3:
        return [int(np.mean(series))] * steps
    try:
        model = ARIMA(series, order=(1,1,1))
        forecast = model.fit().forecast(steps=steps)
        return [max(0, int(round(x))) for x in forecast]
    except:
        return [int(np.mean(series))] * steps

# --- STORE MANAGER ---
if len(selected) == 1:
    row = df.iloc[0]

    def delta(val, key):
        prev = prev_agg.get(key, 0)
        if prev == 0:
            return "N/A"
        pct = (val - prev) / prev * 100
        return f"{pct:+.1f}%"

    st.header(f"{row['name']} – {period_option.replace('_', ' ').title()}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}", delta(row['count_in'], 'count_in'))
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%", delta(row['conversion_rate'], 'conversion_rate'))
    c3.metric("Omzet", f"€{int(row['turnover']):,}", delta(row['turnover'], 'turnover'))
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}", delta(row['sales_per_visitor'], 'sales_per_visitor'))

    # Dagelijks
    daily = df_raw[["date", "count_in", "conversion_rate", "turnover", "sales_per_visitor"]].copy()
    daily["date"] = daily["date"].dt.strftime("%a %d")
    st.subheader("Dagelijks")
    st.dataframe(daily.style.format({"count_in": "{:,}", "conversion_rate": "{:.1f}%", "turnover": "€{:.0f}", "sales_per_visitor": "€{:.2f}"}))

    # Voorspelling
    hist_footfall = df_raw["count_in"].fillna(0).astype(int).tolist()
    forecast_footfall = forecast_series(hist_footfall, 7)
    future = pd.date_range(today + pd.Timedelta(days=1), periods=7)

    forecast_turnover = []
    for i, d in enumerate(future):
        wd = d.weekday()
        conv = weekday_avg.loc[wd, "conversion_rate"] / 100
        spt = weekday_avg.loc[wd, "sales_per_transaction"]
        turnover = forecast_footfall[i] * conv * spt
        forecast_turnover.append(int(round(turnover)))

    forecast_df = pd.DataFrame({"Dag": future.strftime("%a %d"), "Verw. Footfall": forecast_footfall, "Verw. Omzet": forecast_turnover})
    st.subheader("Voorspelling komende 7 dagen")
    st.dataframe(forecast_df.style.format({"Verw. Footfall": "{:,}", "Verw. Omzet": "€{:,}"}))

    # Grafiek
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["count_in"], name="Footfall", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=daily["date"], y=daily["turnover"], name="Omzet", marker_color="#ff7f0e"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Footfall"], name="Voorsp. Footfall", marker_color="#17becf"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))
    fig.update_layout(barmode="group", title="Historisch vs Voorspelling", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    # Actie
    if row["conversion_rate"] < 12:
        st.warning("**Actie nodig:** Conversie <12% → +1 FTE piekuren = +3–5% conversie")
    else:
        st.success("**Top:** Conversie boven benchmark → focus op upselling & SPV")
        
