# --- VOORSPELLING + WEER + GRAFIEK (REALISTISCH + WEER OP HISTORIE) ---
daily = df_raw[df_raw["shop_id"] == row["shop_id"]].copy()
daily["dag"] = daily["date"].dt.strftime("%a %d")

# REALISTISCHE VOORSPELLING (zoals vorige week – +25-40% op vr/za + Black Friday boost)
recent = df_full[(df_full["date"] >= today - pd.Timedelta(days=60)) & (df_full["shop_id"] == row["shop_id"])]
hist_footfall = recent["count_in"].fillna(300).astype(int).tolist()

def forecast_realistic(series, steps=7):
    if len(series) < 10:
        base = int(np.mean(series or [350]))
    else:
        base = int(np.percentile(series[-30:], 70))  # neem 70e percentiel van laatste maand
    forecast = []
    for i in range(steps):
        day = (today + pd.Timedelta(days=i+1)).weekday()
        multiplier = 1.0
        if day in [4,5]: multiplier = 1.45  # vrijdag/zaterdag boost
        if (today + pd.Timedelta(days=i+1)).day in range(28, 32): multiplier *= 1.60  # Black Friday week
        forecast.append(int(base * multiplier * 1.08))  # +8% trend
    return forecast

forecast_footfall = forecast_realistic(hist_footfall)
future_dates = pd.date_range(today + pd.Timedelta(days=1), periods=7)
base_conv = max(row["conversion_rate"] / 100, 0.10)
base_spv = max(row.get("sales_per_visitor", 2.8), 2.5)
forecast_turnover = [int(f * base_conv * base_spv * 1.12) for f in forecast_footfall]  # +12% uplift

forecast_df = pd.DataFrame({"Dag": future_dates.strftime("%a %d"), "Verw. Footfall": forecast_footfall, "Verw. Omzet": forecast_turnover})

st.subheader("Voorspelling komende 7 dagen (realistisch + Black Friday boost)")
st.dataframe(forecast_df.style.format({"Verw. Footfall": "{:,}", "Verw. Omzet": "€{:,}"}))

# WEER VOOR HISTORIE + VOORSPELLING
zip_code = next(loc for loc in locations if loc["id"] == shop_ids[0])["zip"][:4]
start_hist = df_raw["date"].min().date() - timedelta(days=1)
end_forecast = today + timedelta(days=8)

weather_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{zip_code}NL/{start_hist}/{end_forecast}?unitGroup=metric&key={VISUALCROSSING_KEY}&include=days"
weather_df = pd.DataFrame()
try:
    r = requests.get(weather_url, timeout=10)
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
    weather_df = pd.DataFrame({"Dag": daily["dag"].tolist() + forecast_df["Dag"].tolist(), "Temp": [8]*20, "Neerslag_mm": [0]*20, "Icon": ["partly-cloudy-day"]*20})

icon_map = {"clear-day": "☀️", "partly-cloudy-day": "⛅", "cloudy": "☁️", "rain": "🌧️", "snow": "❄️"}
weather_df["Weer"] = weather_df["Icon"].map(icon_map).fillna("🌤️")
all_days = daily["dag"].tolist() + forecast_df["Dag"].tolist()
weather_df = weather_df[weather_df["Dag"].isin(all_days)]

# GRAFIEK MET WEER OP HISTORIE
fig = go.Figure()
fig.add_trace(go.Bar(x=daily["dag"], y=daily["count_in"], name="Footfall", marker_color="#1f77b4"))
fig.add_trace(go.Bar(x=daily["dag"], y=daily["turnover"], name="Omzet", marker_color="#ff7f0e"))
fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))
fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Temp"]*50, name="Temp °C ×50", yaxis="y2", line=dict(color="orange", width=4)))
fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Neerslag_mm"]*100, name="Neerslag mm ×100", yaxis="y3", line=dict(color="blue", dash="dot")))

max_y = max(daily["turnover"].max(), max(forecast_turnover)) * 1.25
for _, w in weather_df.iterrows():
    fig.add_annotation(x=w["Dag"], y=max_y, text=w["Weer"], showarrow=False, font=dict(size=28))

fig.update_layout(
    height=750, barmode="group", title="Footfall & Omzet + Weer (historie + voorspelling)",
    yaxis=dict(title="Aantal / Omzet €"),
    yaxis2=dict(title="Temp ×50", overlaying="y", side="right", showgrid=False),
    yaxis3=dict(title="Neerslag ×100", overlaying="y", side="right", position=0.99, showgrid=False),
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white"
)
st.plotly_chart(fig, use_container_width=True)
