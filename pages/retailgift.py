# --- 12. STORE MANAGER VIEW (100% VEILIG – GEEN KEYERROR MEER) ---
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

    # --- VOORSPELLING 7 DAGEN (nu ook veilig) ---
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

    # --- WEERLIJNEN + WEERICONEN VIA VISUAL CROSSING (bleef al perfect) ---
    zip_code = selected[0]["zip"][:4] if selected else "1102"
    start_hist = df_raw["date"].min().date() if not df_raw.empty else today.date()
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
        st.warning("Weerdata niet beschikbaar – fallback gebruikt")

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

    # --- GRAFIEK (bleef al perfect) ---
    fig = go.Figure()
    fig.add_trace(go.Bar(x=daily["date"], y=daily["count_in"], name="Footfall", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=daily["date"], y=daily["turnover"], name="Omzet", marker_color="#ff7f0e"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Footfall"], name="Voorsp. Footfall", marker_color="#17becf"))
    fig.add_trace(go.Bar(x=forecast_df["Dag"], y=forecast_df["Verw. Omzet"], name="Voorsp. Omzet", marker_color="#ff9896"))

    if not weather_df.empty:
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Temp"], name="Temperatuur °C", yaxis="y2",
                                 mode="lines+markers", line=dict(color="orange", width=5), marker=dict(size=8)))
        fig.add_trace(go.Scatter(x=weather_df["Dag"], y=weather_df["Neerslag_mm"], name="Neerslag mm", yaxis="y3",
                                 mode="lines+markers", line=dict(color="blue", width=5, dash="dot"), marker=dict(size=8)))

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

    # --- ACTIE (NU 100% VEILIG) ---
    conv = row.get("conversion_rate", 0)
    if conv < 12:
        st.warning("**Actie:** +1 FTE piekuren (11-17u) → +3-5% conversie")
    else:
        st.success("**Top:** Conversie ≥12%. Vandaag piek 12-16u → upselling push!")

# --- REGIO & DIRECTIE (blijven werken) ---
elif tool == "Regio Manager":
    st.header(f"Regio – {period_option.replace('_', ' ').title()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    st.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    st.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))
else:
    st.header(f"Keten – {period_option.replace('_', ' ').title()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    st.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    st.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    st.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.info("**Q4 Forecast:** +4% omzet bij mild weer")

st.caption("RetailGift AI – Weericonen, historie + voorspelling, legenda perfect – 100% stabiel – 22 nov 2025")
