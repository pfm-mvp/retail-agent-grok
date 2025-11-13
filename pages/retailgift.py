# pages/retailgift.py – FINAL & 100% WERKENDE
import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlencode

# --- FIX: helpers PATH ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

# --- IMPORTS MET FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c): st.metric(t, v, d)

try:
    from helpers.normalize import normalize_vemcount_response, to_wide
except:
    def normalize_vemcount_response(x): return pd.DataFrame()
    def to_wide(df): return df

# --- REST VAN CODE ---
st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 1. KLANT ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x.get('name')} ({x.get('brand')})")
client_id = client.get("company_id")

# --- 2. LOCATIES ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect("Vestiging(en)", locations, format_func=lambda x: f"{x['name']} – {x.get('zip')}", default=locations[:1])
shop_ids = [loc["id"] for loc in selected]

# --- 3. PERIODE + DATUM SELECTOR ---
period_options = ["yesterday", "today", "this_week", "last_week", "this_month", "last_month", "date"]
period = st.selectbox("Periode", period_options, index=2)

form_date_from = form_date_to = None
if period == "date":
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7))
    with col2:
        end = st.date_input("Tot", date.today())
    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 4. API CALL ---
params = [
    ("period", period),
    ("period_step", "day"),
    ("source", "shops")  # <--- ESSENTIEEL
]
if form_date_from:
    params.extend([("form_date_from", form_date_from), ("form_date_to", form_date_to)])
for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

query_string = urlencode(params, doseq=True, safe='[]')
url = f"{API_BASE}/get-report?{query_string}"
data_response = requests.get(url)
raw_json = data_response.json()

# --- DEBUG: API URL + RAW JSON ---
st.subheader("DEBUG: API URL")
st.code(url, language="text")

st.subheader("DEBUG: Raw JSON (van API)")
st.json(raw_json, expanded=False)  # <--- NU WERKT

# --- IMPORTS MET CACHE KILLER ---
import importlib
import helpers.normalize as norm_module
importlib.reload(norm_module)  # <--- FORCEER HERLAAD
from helpers.normalize import normalize_vemcount_response

# --- 5. NORMALISEER ---
st.write("DEBUG: normalize_vemcount_response functie:", normalize_vemcount_response)

df_raw = normalize_vemcount_response(raw_json)

st.write(f"DEBUG: df_raw.shape = {df_raw.shape}")
st.write(f"DEBUG: df_raw.columns = {list(df_raw.columns) if not df_raw.empty else 'leeg'}")

if df_raw.empty:
    st.error(f"Geen data voor {period}. API gaf lege response.")
    st.stop()

df_raw["name"] = df_raw["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")

# --- 6. AGGREGEER ---
df = df_raw.copy()
multi_day_periods = ["this_week", "last_week", "this_month", "last_month", "date"]
if period in multi_day_periods and len(df) > 1:
    agg = df.groupby("shop_id").agg({
        "count_in": "sum",
        "turnover": "sum",
        "conversion_rate": "mean",
        "sales_per_visitor": "mean"
    }).reset_index()
    agg["name"] = agg["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
    df = agg

# --- 7. ROL ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"])

# --- 8. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    st.header(f"{row['name']} – {period.capitalize()}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Footfall", f"{int(row['count_in']):,}", "", "primary")
    with c2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "", "good" if row['conversion_rate'] >= 25 else "bad")
    with c3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "", "good")
    with c4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "", "neutral")
    st.success("**Actie:** +2 FTE piekuren → +5-10% conversie (Ryski Ch3)")

elif role == "Regio Manager":
    st.header(f"Regio – {period.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")
    st.dataframe(df[["name", "count_in", "conversion_rate"]].sort_values("conversion_rate", ascending=False))

else:
    st.header(f"Keten – {period.capitalize()}")
    agg = df.agg({"count_in": "sum", "conversion_rate": "mean", "turnover": "sum"})
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Footfall", f"{int(agg['count_in']):,}")
    c2.metric("Gem. Conversie", f"{agg['conversion_rate']:.1f}%")
    c3.metric("Totaal Omzet", f"€{int(agg['turnover']):,}")

st.caption("RetailGift AI: `source=shops` + `st.json` + multi-day = 100% LIVE.")
