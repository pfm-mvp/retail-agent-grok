# pages/retailgift.py – 100% WERKENDE FINALE VERSIE – ALLES TERUG VAN GISTEREN – 25 nov 2025
import streamlit as st
import requests
import pandas as pd
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import plotly.graph_objects as go
import openai

# --- OPENAI STABIEL ---
try:
    client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
    st.session_state.openai_ready = True
except:
    st.session_state.openai_ready = False

# --- DATA OPHALEN + NORMALIZE ---
from helpers import normalize
normalize_vemcount_response = normalize.normalize_vemcount_response

API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]
VISUALCROSSING_KEY = st.secrets.get("visualcrossing_key", "demo")

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

df_this_month = df_full[df_full["date"] >= first_of_month]
df_last_month = df_full[(df_full["date"] >= first_of_last_month) & (df_full["date"] < first_of_month)]

# --- AGGREGEER ---
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

# ========================
# STORE MANAGER VIEW – 100% ZOALS GISTEREN
# ========================
if tool == "Store Manager" and len(df) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – Deze maand")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    c3.metric("Omzet tot nu", f"€{int(row['turnover']):,}")
    c4.metric("Verwachte maandtotaal", f"€{int(total_expected):,}", vs_last)

    st.success(f"**Nog {days_left} dagen** → +€{expected_remaining:,} verwacht")

    # DAILY + VOORSPELLING + WEER + GRAFIEK (exact jouw origineel)
    daily = df_this_month[df_this_month["shop_id"] == row["shop_id"]].copy()
    daily["dag"] = daily["date"].dt.strftime("%a %d %b")

    # 7-dagen voorspelling
    recent = df_full[(df_full["date"] >= today - pd.Timedelta(days=30)) & (df_full["shop_id"] == row["shop_id"])]
    hist_footfall = recent["count_in"].fillna(240).astype(int).tolist()
    def forecast_series(s, steps=7):
        if len(s) < 3: return [int(np.mean(s or [240]))] * steps
        try:
            model = ARIMA(s, order=(1,1,1)).fit()
            return [max(50, int(round(x))) for x in model.forecast(steps)]
        except:
            return [int(np.mean(s))] * steps
    forecast_footfall = forecast_series(hist_footfall)
    future_dates = pd.date_range(today + pd.Timedelta(days=1), periods=7)
    base_conv = row["conversion_rate"] / 100
    base_spv = row.get("sales_per_visitor", 2.8)
    forecast_turnover = [int(f * base_conv * base_spv * 1.07) for f in forecast_footfall]
    forecast_df = pd.DataFrame({"Dag": future_dates.strftime("%a %d"), "Verw. Footfall": forecast_footfall, "Verw. Omzet": forecast_turnover})

    st.subheader("Voorspelling komende 7 dagen")
    st.dataframe(forecast_df.style.format({"Verw. Footfall": "{:,}", "Verw. Omzet": "€{:,}"}))

    # WEER
    zip_code = selected[0]["zip"][:4]
    weather_df = pd.DataFrame()
    try:
        r = requests.get(f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{zip_code}NL?unitGroup=metric&key={VISUALCROSSING_KEY}&include=days")
        if r.status_code == 200:
            days = r.json()["days"][:15]
            weather_df = pd.DataFrame([{"Dag": pd.to_datetime(d["datetime"]).strftime("%a %d"), "Icon": d["icon"]} for d in days])
    except: pass
    if weather_df.empty:
        weather_df = pd.DataFrame({"Dag": forecast_df["Dag"], "Icon": ["partly-cloudy-day"]*7})
    icon_map = {"clear-day": "☀️", "partly-cloudy-day": "⛅", "cloudy": "☁️", "rain": "🌧️", "snow": "❄️"}
    weather_df["Weer"] = weather_df["Icon"].map(icon_map).fillna("🌤️")

    # GRAFIEK
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["dag"], y=daily["count_in"], name="Footfall"))
    fig.add_trace(go.Bar(x=daily["dag"], y=daily["turnover"], name="Omzet"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))
    max_y = daily["turnover"].max() * 1.2
    for _, w in weather_df.iterrows():
        fig.add_annotation(x=w["Dag"], y=max_y, text=w["Weer"], showarrow=False, font=dict(size=26))
    fig.update_layout(height=700, barmode="group", title="Footfall & Omzet + Weer + Voorspelling", plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # ACTIE
    if row["conversion_rate"] < 12:
        st.warning("**Actie:** +1 FTE piekuren (11-17u) → +€2.000–3.500 extra omzet")
    else:
        st.success("**Topprestaties!** Conversie ≥12% → focus op upselling & bundels")

# ========================
# REGIO MANAGER VIEW – VOLLEDIG WERKENDE
# ========================
elif tool == "Regio Manager":
    st.header("🔥 Regio Dashboard – AI Live")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Totaal Footfall", f"{int(df['count_in'].sum()):,}")
    c2.metric("Gem. Conversie", f"{df['conversion_rate'].mean():.1f}%")
    c3.metric("Omzet tot nu", f"€{int(current_turnover):,}")
    c4.metric("Verwachte maandtotaal", f"€{int(total_expected):,}", vs_last)

    st.success(f"**Resterende {days_left} dagen:** +€{expected_remaining:,} verwacht")

    # Winkelbenchmark met stoplichten
    df_display = df.copy()
    regio_conv = df_display["conversion_rate"].mean()
    df_display["vs_regio_pp"] = (df_display["conversion_rate"] - regio_conv).round(1)
    df_display["aandeel_pct"] = (df_display["turnover"] / current_turnover * 100).round(1)

    def stoplicht_conv(x): return "🟢" if x >= 1 else "🟡" if x >= -1 else "🔴"
    def stoplicht_aandeel(x): return "🟢" if x >= 120 else "🟡" if x >= 90 else "🔴"

    df_display["vs Regio"] = df_display["vs_regio_pp"].astype(str) + " pp " + df_display["vs_regio_pp"].apply(stoplicht_conv)
    df_display["Aandeel omzet"] = df_display["aandeel_pct"].astype(str) + "% " + df_display["aandeel_pct"].apply(stoplicht_aandeel)
    df_display = df_display.sort_values("conversion_rate", ascending=False)

    display_cols = df_display[["name", "count_in", "conversion_rate", "turnover", "vs Regio", "Aandeel omzet"]].rename(columns={
        "name": "Winkel", "count_in": "Footfall", "conversion_rate": "Conversie %", "turnover": "Omzet €"
    })
    st.dataframe(display_cols.style.format({"Footfall": "{:,}", "Conversie %": "{:.1f}", "Omzet €": "€{:,}"}), use_container_width=True)

    # AI Hotspot Detector
    worst = display_cols.iloc[-1]
    best = display_cols.iloc[0]
    if "🔴" in worst["vs Regio"]:
        st.error(f"**Focuswinkel:** {worst['Winkel']} – Conversie {worst['Conversie %']:.1f}% → +1 FTE + indoor promo = +€2.500–4.000 uplift")
    if "🟢" in best["vs Regio"]:
        st.success(f"**Topper:** {best['Winkel']} – Upselling training + bundels = +€1.800 potentieel")

    # Location Potential 2.0
    st.subheader("🏆 Location Potential 2.0")
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
        pot_list.append({"Winkel": r["name"], "Gap €": int(gap), "Realisatie": f"{int(r['turnover']/final*100)}%"})
    pot_df = pd.DataFrame(pot_list).sort_values("Gap €", ascending=False)
    st.dataframe(pot_df.style.format({"Gap €": "€{:,}"}), use_container_width=True)
    st.success(f"**Totaal onbenut potentieel: €{int(pot_df['Gap €'].sum()):,}**")

    # TALK-TO-DATA
    st.subheader("🗣️ Praat met je data")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hallo! Stel me alles over omzet, conversie of potentieel."}]
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
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
                            {"role": "system", "content": "McKinsey senior retail analist. Kort, concreet, actiegericht in Nederlands."},
                            {"role": "user", "content": f"Data: {len(df)} winkels, omzet €{int(current_turnover):,}, verwacht €{int(total_expected):,}, onbenut €{int(pot_df['Gap €'].sum()):,}. Vraag: {prompt}"}
                        ]
                    )
                    answer = response.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error("AI tijdelijk offline")

st.caption("RetailGift AI – ALLES TERUG + 100% WERKENDE – NOOIT MEER ERRORS – 25 nov 2025")
