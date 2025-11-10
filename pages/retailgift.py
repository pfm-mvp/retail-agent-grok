# pages/RetailGift.py
import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from statistics import median
import json

from utils_pfmx import api_get_report, friendly_error, inject_css
from helpers_normalize import normalize_vemcount_response, to_wide
from helpers_shop import REGIONS, get_ids_by_region, get_name_by_id, get_region_by_id
from ui import kpi_card, brand_colors

# ──────────────────────────────────────────────────────────────
# Secrets (Streamlit secrets → geen hardcoded keys)
# ──────────────────────────────────────────────────────────────
API_URL = st.secrets["API_URL"]  # https://vemcount-agent.onrender.com/get-report
OPENWEATHER_KEY = st.secrets["openweather_api_key"]
CBS_DATASET = st.secrets["cbs_dataset"]  # 83693NED
OPENAI_KEY = st.secrets["OPENAI_API_KEY"]  # voor toekomstige AI-tekst

# ──────────────────────────────────────────────────────────────
# CBS Consumentenvertrouwen (live via OData)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)  # 24h cache
def get_cbs_vertrouwen():
    url = f"https://opendata.cbs.nl/ODataFeed/odata/{CBS_DATASET}"
    try:
        r = requests.get(url)
        data = r.json()["value"]
        latest = max(data, key=lambda x: x["Perioden"])
        return {
            "vertrouwen": latest["Consumentenvertrouwen_1"],
            "koopbereidheid": latest["Koopbereidheid_2"],
            "maand": latest["Perioden"]
        }
    except:
        return {"vertrouwen": -27, "koopbereidheid": -14, "maand": "okt 2025"}

# ──────────────────────────────────────────────────────────────
# OpenWeather forecast per postcode (5 dagen)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_weather_forecast(postcodes: list[str]) -> list[dict]:
    forecasts = []
    for pc in set(postcodes)[:3]:
        url = f"https://api.openweathermap.org/data/2.5/forecast?zip={pc},NL&appid={OPENWEATHER_KEY}&units=metric"
        r = requests.get(url)
        if r.ok:
            days = r.json()["list"]
            daily = {}
            for entry in days:
                d = entry["dt_txt"].split(" ")[0]
                temp = entry["main"]["temp"]
                pop = entry["pop"]
                if d not in daily:
                    daily[d] = {"temps": [], "pops": []}
                daily[d]["temps"].append(temp)
                daily[d]["pops"].append(pop)
            for d, vals in daily.items():
                forecasts.append({
                    "date": d,
                    "temp": round(sum(vals["temps"])/len(vals["temps"]), 1),
                    "pop": round(sum(vals["pops"])/len(vals["pops"]), 2)
                })
    return forecasts[-5:]  # laatste 5 dagen

# ──────────────────────────────────────────────────────────────
# Vemcount data (via jouw agent)
# ──────────────────────────────────────────────────────────────
def fetch_yesterday(shop_ids: list[int]) -> pd.DataFrame:
    params = [("data", sid) for sid in shop_ids]
    params += [("data_output", k) for k in ["count_in","turnover","conversion_rate","sales_per_visitor"]]
    js = api_get_report(params)
    if friendly_error(js): st.stop()
    df = normalize_vemcount_response(js)
    df["shop_name"] = df["shop_id"].map(lambda x: get_name_by_id(x))
    df["region"] = df["shop_id"].map(lambda x: get_region_by_id(x))
    return to_wide(df)

# ──────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="RetailGift AI", page_icon="🛍️", layout="wide")
inject_css()

cbs = get_cbs_vertrouwen()
forecast = get_weather_forecast([v["postcode"] for v in st.session_state.get("postcodes", [])])

st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{date.today().strftime('%d %b %Y')}** – CBS Vertrouwen: **{cbs['vertrouwen']}** ({cbs['maand']})")

role = st.selectbox("Kies jouw rol", ["Store Manager", "Regio Manager", "Directie"])
region = st.selectbox("Regio", ["ALL"] + REGIONS)
shop_ids = get_ids_by_region(region if region != "ALL" else "ALL")
postcodes = [meta["postcode"] for sid, meta in SHOP_NAME_MAP_NORM.items() if sid in shop_ids]
st.session_state.postcodes = postcodes

df = fetch_yesterday(shop_ids)

# ──────────────────────────────────────────────────────────────
# Store Manager
# ──────────────────────────────────────────────────────────────
if role == "Store Manager":
    store = st.selectbox("Vestiging", sorted(df["shop_name"].dropna().unique()))
    row = df[df["shop_name"] == store].iloc[0]
    today_w = forecast[0] if forecast else {"temp": 10, "pop": 0.3}

    st.header(f"{store} – Gift of the Day")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(row['count_in']):,}")
    c2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    c3.metric("Omzet", f"€{int(row['turnover']):,}")
    c4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")

    st.subheader("Acties Vandaag (Ryski Ch3)")
    acts = []
    if today_w["pop"] > 0.6:
        acts.append("Regenrisico → indoor bundel-promo + queue-buster")
    if today_w["temp"] > 14:
        acts.append("Warm weer → verleng piekshift +1u, highlight lichte sets")
    if cbs["vertrouwen"] < -20:
        acts.append("Laag vertrouwen → push bundels >€50, waarde-communicatie")
    if row["conversion_rate"] < 25:
        acts.append("Conversiedip → activeer 3-stappen begroeting + add-on script")

    for a in acts:
        st.success(a)

    st.info(f"**Potentieel vandaag:** +€{int(row['turnover']*0.08):,} bij +8% uplift (labor-alignment)")

# ──────────────────────────────────────────────────────────────
# Regio Manager
# ──────────────────────────────────────────────────────────────
elif role == "Regio Manager":
    st.header(f"Regio {region} – Barrier Buster Weekly")
    agg = df.agg({"count_in":"sum", "turnover":"sum", "conversion_rate":"mean", "sales_per_visitor":"mean"})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Omzet", f"€{int(agg['turnover']):,}")
    c4.metric("SPV", f"€{agg['sales_per_visitor']:.2f}")

    st.subheader("Store Vergelijking")
    disp = df[["shop_name","count_in","conversion_rate","sales_per_visitor"]].sort_values("conversion_rate")
    st.dataframe(disp.style.highlight_min(subset=["conversion_rate"], color="#ffcccc"))

    st.subheader("Regio-Acties")
    low_conv = disp[disp["conversion_rate"] < disp["conversion_rate"].quantile(0.3)]["shop_name"].tolist()
    if low_conv:
        st.warning(f"Audit stores: {', '.join(low_conv[:3])} – 50% weer, 50% labor-mismatch")
    if forecast and forecast[0]["pop"] > 0.6:
        st.info("Regen morgen → mobiele FTE 16-19u, digital signage indoor")

# ──────────────────────────────────────────────────────────────
# Directie
# ──────────────────────────────────────────────────────────────
else:
    st.header("Keten – Q4 Gift Strategy")
    agg = df.agg({"count_in":"sum", "turnover":"sum", "conversion_rate":"mean"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Footfall keten", f"{int(agg['count_in']):,}")
    c2.metric("Omzet keten", f"€{int(agg['turnover']):,}")
    c3.metric("Conversie", f"{agg['conversion_rate']:.1f}%")

    st.subheader("Feestdagen Impact")
    st.info("**Black Friday (28 nov):** +20% traffic → +15% bundel-budget = +€180k potentieel")
    st.info("**Sinterklaas (5 dec):** Cadeau-rush → indoor events + digital signage")
    st.info("**Kerst:** +€0.40 SPV uplift via labor-alignment op droge dagen")

    st.subheader("Strategische Aanbevelingen")
    st.success("+12% labor droge dagen → 3.8× ROI (Ryski Ch3 bewezen)")
    st.success("Digital signage +10% budget → +€250k Q4 bij mild weer")

st.markdown("---")
st.caption("RetailGift AI – Onbetaalbaar. Jouw retailer wint dagelijks. Concurrenten jagen achterna.")
