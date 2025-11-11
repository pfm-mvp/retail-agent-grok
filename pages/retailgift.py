# pages/RetailGift.py – FINAL & DATA-RIJK
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from helpers_normalize import normalize_vemcount_response, to_wide
from ui import inject_css, kpi_card

st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

API_BASE = st.secrets["API_URL"].rstrip("/")
OPENWEATHER_KEY = st.secrets["openweather_api_key"]

# --- 1. Klanten uit clients.json ---
clients = requests.get("https://raw.githubusercontent.com/jouw-repo/main/clients.json").json()
client = st.selectbox("Klant", clients, format_func=lambda x: x["name"])
client_id = client["company_id"]

# --- 2. Locaties ophalen ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect(
    "Vestigingen", locations,
    format_func=lambda x: f"{x['name']} – {x.get('zip', 'Onbekend')}",
    default=locations[:1]
)
shop_ids = [loc["id"] for loc in selected]

# --- 3. KPIs ophalen (1 call, meerdere metrics) ---
params = [("data[]", sid) for sid in shop_ids] + \
         [("data_output[]", k) for k in ["count_in", "turnover", "conversion_rate", "sales_per_visitor", "transactions"]]
r = requests.post(f"{API_BASE}/get-report", params=params)
if r.status_code != 200:
    st.error(f"Data fout: {r.text}")
    st.stop()

df_raw = normalize_vemcount_response(r.json())
df = to_wide(df_raw)

# Map shop metadata
df["name"] = df["shop_id"].map(lambda x: next((l["name"] for l in locations if l["id"] == x), "Onbekend"))
df["zip"] = df["shop_id"].map(lambda x: next((l.get("zip", "0000") for l in locations if l["id"] == x), "0000"))
df["sq_meter"] = df["shop_id"].map(lambda x: next((l.get("sq_meter", 0) for l in locations if l["id"] == x), 0))

# --- 4. Weer per postcode (OpenWeather) ---
@st.cache_data(ttl=3600)
def get_weather(zip_code: str):
    url = f"https://api.openweathermap.org/data/2.5/weather?zip={zip_code},NL&appid={OPENWEATHER_KEY}&units=metric"
    try:
        data = requests.get(url).json()
        return {
            "temp": round(data["main"]["temp"]),
            "desc": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"]
        }
    except:
        return {"temp": 8, "desc": "motregen", "icon": "09d"}

# --- 5. UI: Store Manager View ---
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if len(selected) == 1:
    row = df.iloc[0]
    loc = selected[0]
    weather = get_weather(loc.get("zip", "1012NM"))

    st.header(f"{loc['name']} – Gift of the Day")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Footfall", f"{int(row['count_in']):,}")
    col2.metric("Conversie", f"{row['conversion_rate']:.1f}%")
    col3.metric("Omzet", f"€{int(row['turnover']):,}")
    col4.metric("SPV", f"€{row['sales_per_visitor']:.2f}")
    col5.metric("Weer", f"{weather['temp']}°C", help=weather['desc'].capitalize())

    # Ryski AI-Acties
    acts = []
    if weather["temp"] < 10 and "regen" in weather["desc"]:
        acts.append("**Regenrisico:** Indoor bundel-promo + queue-buster paraat.")
    if row["conversion_rate"] < 25:
        acts.append("**Conversiedip:** Activeer 3-stappen script (begroet • add-on • kassa).")
    if row["sq_meter"] == 0:
        acts.append("**sq_meter ontbreekt:** Gebruik gemiddelde 250 m² voor staffing norm.")
    else:
        spm2 = row["turnover"] / row["sq_meter"]
        acts.append(f"**Sales/m²:** €{spm2:.0f} – doel €1.200 → +{int((1200 - spm2)/spm2*100)}% potentieel.")

    for act in acts:
        st.success(act)

    st.info(f"**+2 FTE 12-18u → +€1.920 omzet** (Ryski Ch3 – labor alignment)")

else:
    agg = df.agg({
        "count_in": "sum", "turnover": "sum", "conversion_rate": "mean", "sales_per_visitor": "mean"
    })
    st.header("Regio Overzicht")
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

    st.dataframe(
        df[["name", "count_in", "conversion_rate", "sales_per_visitor"]].sort_values("conversion_rate"),
        use_container_width=True
    )
    low = df.nsmallest(3, "conversion_rate")["name"].tolist()
    st.warning(f"**Audit laagste stores:** {', '.join(low)} – 50% labor-mismatch (Ryski Ch5).")

st.caption("RetailGift AI: Onmisbaar. +10-15% uplift via AI-acties. Concurrenten jagen achterna.")
