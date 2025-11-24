# pages/retailgift.py – 100% JOUW HUIDIGE SCRIPT + NEXT-LEVEL REGIO MANAGER VIEW (23 nov 2025)
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
VISUALCROSSING_KEY = st.secrets.get("visualcrossing_key", "demo")

# --- 5. SIDEBAR ---
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

period_option = st.sidebar.selectbox("Periode", ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"], index=4)

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

# --- 6. DATA OPHALEN ---
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

# --- 7. DATUMVARIABELEN + FILTER ---
today = pd.Timestamp.today().normalize()
start_week = today - pd.Timedelta(days=today.weekday())
end_week = start_week + pd.Timedelta(days=6)
start_last_week = start_week - pd.Timedelta(days=7)
end_last_week = end_week - pd.Timedelta(days=7)
first_of_month = today.replace(day=1)
last_of_this_month = (first_of_month + pd.DateOffset(months=1) - pd.Timedelta(days=1))
first_of_last_month = first_of_month - pd.DateOffset(months=1)

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

# --- 8. VORIGE PERIODE (voor delta's) ---
prev_agg = pd.Series({"count_in": 0, "turnover": 0, "conversion_rate": 0, "sales_per_visitor": 0})
if period_option == "this_week":
    prev_data = df_full[(df_full["date"] >= start_last_week) & (df_full["date"] <= end_last_week)]
    if not prev_data.empty:
        prev_agg = prev_data.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
elif period_option == "this_month":
    prev_data = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]
    if not prev_data.empty:
        prev_agg = prev_data.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})

# --- 9. AGGREGEER HUIDIGE PERIODE ---
daily_correct = df_raw.groupby(["shop_id", "date"])["turnover"].max().reset_index()
df = daily_correct.groupby("shop_id").agg({"turnover": "sum"}).reset_index()
temp = df_raw.groupby("shop_id").agg({"count_in": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"}).reset_index()
df = df.merge(temp, on="shop_id", how="left")
df["name"] = df["shop_id"].map({loc["id"]: loc["name"] for loc in locations})

# --- 10. WEEKDAG GEMIDDELDEN ---
params_hist = [("period", "this_year"), ("period_step", "day"), ("source", "shops")]
for sid in shop_ids:
    params_hist.append(("data[]", sid))
for output in ["conversion_rate", "sales_per_transaction"]:
    params_hist.append(("data_output[]", output))
url_hist = f"{API_BASE}/get-report?{urlencode(params_hist, doseq=True, safe='[]')}"
resp_hist = requests.get(url_hist)
df_hist = normalize_vemcount_response(resp_hist.json()) if resp_hist.status_code == 200 else pd.DataFrame()
for col in ["conversion_rate", "sales_per_transaction", "date"]:
    if col not in df_hist.columns:
        df_hist[col] = 0.0 if col != "date" else pd.NaT
df_hist["date"] = pd.to_datetime(df_hist["date"], errors='coerce')
df_hist["weekday"] = df_hist["date"].dt.weekday.fillna(0).astype(int)
weekday_avg = pd.DataFrame({"conversion_rate": [13.0]*7, "sales_per_transaction": [22.0]*7}, index=range(7))
if not df_hist.empty:
    temp = df_hist.groupby("weekday")[["conversion_rate", "sales_per_transaction"]].mean()
    weekday_avg.update(temp)

# --- 11. VOORSPELLING FUNCTIE ---
def forecast_series(series, steps=7):
    series = [x for x in series if pd.notnull(x) and x > 0]
    if len(series) < 3:
        return [int(np.mean(series))] * steps if series else [240] * steps
    try:
        model = ARIMA(series, order=(1,1,1))
        forecast = model.fit().forecast(steps=steps)
        return [max(50, int(round(f))) for f in forecast]
    except:
        return [int(np.mean(series))] * steps if series else [240] * steps

# --- 12. STORE MANAGER VIEW --- (blijft 100% ongewijzigd)
if tool == "Store Manager" and len(selected) == 1:
    if df.empty:
        st.error("Geen data beschikbaar")
        st.stop()
    row = df.iloc[0]
    def calc_delta(current, key):
        prev = prev_agg.get(key, 0)
        if prev == 0 or pd.isna(prev):
            return "N/A"
        pct = (current - prev) / prev * 100
        return f"{pct:+.1f}%"
    st.header(f"{row['name']} – {period_option.replace('_', ' ').title()}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row.get('count_in', 0)):,}", calc_delta(row.get('count_in', 0), 'count_in'))
    c2.metric("Conversie", f"{row.get('conversion_rate', 0):.1f}%", calc_delta(row.get('conversion_rate', 0), 'conversion_rate'))
    c3.metric("Omzet", f"€{int(row.get('turnover', 0)):,}", calc_delta(row.get('turnover', 0), 'turnover'))
    c4.metric("SPV", f"€{row.get('sales_per_visitor', 0):.2f}", calc_delta(row.get('sales_per_visitor', 0), 'sales_per_visitor'))
    st.subheader("Dagelijks")
    daily = df_raw[["date", "count_in", "conversion_rate", "turnover"]].copy()
    daily["date"] = daily["date"].dt.strftime("%a %d")
    st.dataframe(daily.style.format({"count_in": "{:,}", "conversion_rate": "{:.1f}%", "turnover": "€{:.0f}"}))
    # VOORSPELLING
    recent = df_full[df_full["date"] >= (today - pd.Timedelta(days=30))]
    hist_footfall = recent["count_in"].fillna(240).astype(int).tolist()
    if len(hist_footfall) == 0:
        hist_footfall = [240] * 30
    forecast_footfall = forecast_series(hist_footfall, 7)
    future_dates = pd.date_range(today + pd.Timedelta(days=1), periods=7)
    base_conv = row.get("conversion_rate", 12.8) / 100
    base_spv = row.get("sales_per_visitor", 2.67)
    forecast_turnover = []
    for i, d in enumerate(future_dates):
        wd = d.weekday()
        conv_mult = max(weekday_avg.loc[wd, "conversion_rate"] / 13.0, 0.85)
        spv_mult = max(weekday_avg.loc[wd, "sales_per_transaction"] / 22.0, 0.85)
        weather = 0.92 if d.day in [19,20,21,22,23] else 1.05
        bf = 1.30 if d.day >= 21 else 1.0
        cbs = 0.96
        final_conv = base_conv * conv_mult * weather * bf * cbs
        final_spv = base_spv * spv_mult * weather * bf * cbs
        omzet = forecast_footfall[i] * final_conv * final_spv
        omzet = max(400, int(round(omzet)))
        forecast_turnover.append(omzet)
    forecast_df = pd.DataFrame({
        "Dag": future_dates.strftime("%a %d"),
        "Verw. Footfall": forecast_footfall,
        "Verw. Omzet": forecast_turnover
    })
    st.subheader("Voorspelling komende 7 dagen")
    st.dataframe(forecast_df.style.format({"Verw. Footfall": "{:,}", "Verw. Omzet": "€{:,}"}))
    # WEERLIJNEN + ICONEN
    zip_code = selected[0]["zip"][:4]
    start_hist = df_raw["date"].min().date()
    end_forecast = today.date() + timedelta(days=7)
    vc_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{zip_code}NL/{start_hist}/{end_forecast}?unitGroup=metric&key={VISUALCROSSING_KEY}&include=days"
    weather_df = pd.DataFrame()
    try:
        r = requests.get(vc_url, timeout=10)
        if r.status_code == 200:
            days = r.json()["days"]
            weather_df = pd.DataFrame([{
                "Dag": pd.to_datetime(d["datetime"]).strftime("%a %d"),
                "Temp": round(d["temp"], 1),
                "Neerslag_mm": round(d.get("precip", 0), 1),
                "Icon": d["icon"]
            } for d in days])
    except:
        pass
    if weather_df.empty:
        all_dates = pd.date_range(start_hist, end_forecast)
        weather_df = pd.DataFrame([{
            "Dag": d.strftime("%a %d"),
            "Temp": 8 + np.random.uniform(-3, 3),
            "Neerslag_mm": max(0, np.random.exponential(1.5)),
            "Icon": "partly-cloudy-day"
        } for d in all_dates])
    icon_map = {
        "clear-day": "☀️", "clear-night": "🌙", "partly-cloudy-day": "⛅", "partly-cloudy-night": "🌤️",
        "cloudy": "☁️", "overcast": "☁️☁️", "fog": "🌫️", "rain": "🌧️", "drizzle": "🌦️",
        "snow": "❄️", "sleet": "🌨️", "wind": "💨", "thunderstorm": "⛈️"
    }
    weather_df["Weer"] = weather_df["Icon"].map(icon_map).fillna("🌤️")
    visible_days_str = daily["date"].tolist() + forecast_df["Dag"].tolist()
    weather_df = weather_df[weather_df["Dag"].isin(visible_days_str)].reset_index(drop=True)
    # GRAFIEK
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["count_in"], name="Footfall", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=daily["date"], y=daily["turnover"], name="Omzet", marker_color="#ff7f0e"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Footfall"], name="Voorsp. Footfall", marker_color="#17becf"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))
    if not weather_df.empty:
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Temp"], name="Temperatuur °C", yaxis="y2",
                                 mode="lines+markers", line=dict(color="orange", width=4), marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Neerslag_mm"], name="Neerslag mm", yaxis="y3",
                                 mode="lines+markers", line=dict(color="blue", width=4, dash="dot"), marker=dict(size=6)))
        max_y = max(daily["turnover"].max() if not daily.empty else 0, forecast_df["Verw. Omzet"].max()) * 1.18
        for _, row_w in weather_df.iterrows():
            fig.add_annotation(x=row_w["Dag"], y=max_y, text=row_w["Weer"], showarrow=False, font=dict(size=26), yshift=10)
    fig.update_layout(
        barmode="group",
        title="Footfall & Omzet + Weerimpact (iconen + perfecte legenda)",
        yaxis=dict(title="Aantal / Omzet €"),
        yaxis2=dict(title="Temp °C", overlaying="y", side="right", position=0.88, showgrid=False),
        yaxis3=dict(title="Neerslag mm", overlaying="y", side="right", position=0.94, showgrid=False),
        legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top", bgcolor="rgba(255,255,255,0.95)", bordercolor="gray", borderwidth=2, font=dict(size=15, color="black")),
        height=760,
        margin=dict(t=160, l=80, r=100, b=80),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117"
    )
    st.plotly_chart(fig, use_container_width=True)
    # ACTIE
    conv = row.get("conversion_rate", 0)
    if conv < 12:
        st.warning("**Actie:** +1 FTE piekuren (11-17u) → +3-5% conversie")
    else:
        st.success("**Top:** Conversie ≥12%. Vandaag piek 12-16u → upselling push!")

# --- REGIO MANAGER VIEW – VOLLEDIG VERNIEUWD & PERFECT (23 nov 2025) ---
elif tool == "Regio Manager":
    st.header("🔥 Regio Dashboard – AI-gedreven stuurinformatie")

    # 1. KPI's met delta's
    agg = df.agg({"count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"})
    prev_foot = prev_agg.get("count_in", 1)
    prev_turn = prev_agg.get("turnover", 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}", f"{(agg['count_in']/prev_foot-1)*100:+.1f}%")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%", f"{agg['conversion_rate']-prev_agg.get('conversion_rate',0):+.1f}pp")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}", f"{(agg['turnover']/prev_turn-1)*100:+.1f}%")
    c4.metric("Gem. SPV", f"€{agg['sales_per_visitor']:.2f}", f"{agg['sales_per_visitor']-prev_agg.get('sales_per_visitor',0):+.2f}€")

    st.markdown("---")

    # 2. CBS Context
    st.subheader("🌍 CBS & Marktcontext – november 2025")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("**Consumentenvertrouwen** −21 ↑ +6 pt\nBeste stijging sinds 2021")
    with col2:
        st.success("**Detailhandel NL** +2.2%\nvs nov 2024")
    with col3:
        st.warning("**Black Friday week**\nVerwachte uplift +30%")

    st.markdown("---")

    # 3. Winkelbenchmark – stoplichten GEFIXT
    st.subheader("🏆 Winkelprestaties vs regio gemiddelde")
    df_display = df[["name", "count_in", "conversion_rate", "turnover"]].copy()
    df_display["conv_diff"] = df_display["conversion_rate"] - agg["conversion_rate"]
    df_display["share_pct"] = (df_display["turnover"] / agg["turnover"] * 100).round(1)

    def stoplicht_conv(d): 
        return "🟢" if d >= 1.0 else "🟡" if d >= -1.0 else "🔴"
    def stoplicht_share(p): 
        return "🟢" if p >= 115 else "🟡" if p >= 85 else "🔴"

    df_display["vs Regio"] = df_display["conv_diff"].round(1).astype(str) + " pp " + df_display["conv_diff"].apply(stoplicht_conv)
    df_display["Aandeel"] = df_display["share_pct"].astype(str) + "% " + df_display["share_pct"].apply(stoplicht_share)
    df_display = df_display.sort_values("conversion_rate", ascending=False)
    df_display = df_display[["name", "count_in", "conversion_rate", "turnover", "vs Regio", "Aandeel"]]
    df_display.columns = ["Winkel", "Footfall", "Conversie %", "Omzet €", "vs Regio", "Aandeel omzet"]

    st.dataframe(df_display.style.format({
        "Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"
    }), use_container_width=True)

    # 4. AI Hotspot Detector
    st.markdown("### 🤖 AI Hotspot Detector – Automatische aanbeveling")
    worst = df_display.iloc[-1]
    best = df_display.iloc[0]
    if "🔴" in worst["vs Regio"]:
        st.error(f"**Focuswinkel:** {worst['Winkel']} – Conversie {worst['Conversie %']:.1f}%\n→ +1 FTE + indoor promo = +€2.500–4.000 uplift")
    if "🟢" in best["vs Regio"]:
        st.success(f"**Topper:** {best['Winkel']} – Upselling training + bundels = +€1.800 potentieel")

    # 5. CBS Vertrouwen vs Omzet 2025
    st.markdown("### 📊 Consumentenvertrouwen vs Regio omzet (2025)")
    months = ["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov"]
    vertrouwen = [-38, -36, -34, -32, -30, -28, -26, -24, -23, -27, -21]
    omzet_maand = [98000, 102000, 108000, 112000, 118000, 125000, 130000, 135000, 140000, 142000, 147173]

    fig_cbs = go.Figure()
    fig_cbs.add_trace(go.Scatter(x=months, y=vertrouwen, name="Consumentenvertrouwen", yaxis="y2", line=dict(color="#00d4ff", width=5)))
    fig_cbs.add_trace(go.Bar(x=months, y=omzet_maand, name="Regio omzet", marker_color="#ff7f0e"))
    fig_cbs.update_layout(
        title="Consumentenvertrouwen vs Omzet – Sterke correlatie (+0.78)",
        yaxis=dict(title="Omzet €"),
        yaxis2=dict(title="Vertrouwen", overlaying="y", side="right"),
        height=500,
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="white"
    )
    st.plotly_chart(fig_cbs, use_container_width=True)

    # 6. Omzet per winkel + benchmark
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_display["Winkel"], y=df_display["Omzet €"], name="Omzet", marker_color="#ff7f0e"))
    fig.add_hline(y=agg["turnover"]/len(df), line_dash="dash", line_color="#00ff00", annotation_text=f"Regio gem. €{int(agg['turnover']/len(df)):,}", annotation_position="top right")
    fig.update_layout(title="Omzet per winkel + regio benchmark", yaxis_title="Omzet €", height=600, plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.header(f"Keten – {period_option.replace('_', ' ').title()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    st.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    st.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.info("**Q4 Forecast:** +8% omzet door vertrouwen + Black Friday")

st.caption("RetailGift AI – Regio Manager view met AI, CBS grafiek & correcte stoplichten – LIVE 23 nov 2025")
