# pages/retailgift.py – FINAL & 100% WERKENDE + VRIJE DATUM OF FIXED PERIODE
import streamlit as st
import requests
import pandas as pd
import sys
import os
from datetime import date, timedelta
from urllib.parse import urlencode
import importlib

# --- 1. FIX: helpers PATH + RELOAD normalize ---
current_dir = os.path.dirname(os.path.abspath(__file__))
helpers_path = os.path.join(current_dir, "..", "helpers")
if helpers_path not in sys.path:
    sys.path.append(helpers_path)

import normalize
importlib.reload(normalize)
from normalize import normalize_vemcount_response

# --- 2. IMPORTS MET FALLBACK ---
try:
    from helpers.ui import inject_css, kpi_card
except:
    def inject_css(): st.markdown("", unsafe_allow_html=True)
    def kpi_card(t, v, d, c): st.metric(t, v, d)

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="RetailGift AI", page_icon="STORE TRAFFIC IS A GIFT", layout="wide")
inject_css()

# --- 4. SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- 5. KLANT ---
clients = requests.get(CLIENTS_JSON).json()
client = st.selectbox("Klant", clients, format_func=lambda x: f"{x.get('name')} ({x.get('brand')})")
client_id = client.get("company_id")

# --- 6. LOCATIES ---
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
selected = st.multiselect("Vestiging(en)", locations, format_func=lambda x: f"{x['name']} – {x.get('zip')}", default=locations[:1])
shop_ids = [loc["id"] for loc in selected]

# --- 7. PERIODE SELECTOR ---
fixed_periods = ["yesterday", "today", "this_week", "last_week", "this_month", "last_month"]
period_option = st.selectbox("Periode", fixed_periods + ["date"], index=2)

# --- 8. DATUM SELECTOR (alleen bij "date") ---
form_date_from = form_date_to = None
if period_option == "date":
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Van", date.today() - timedelta(days=7), key="start_date")
    with col2:
        end = st.date_input("Tot", date.today(), key="end_date")

    # VALIDEER: start <= end
    if start > end:
        st.error("**Fout:** 'Van' datum moet vóór 'Tot' datum zijn.")
        st.stop()

    form_date_from = start.strftime("%Y-%m-%d")
    form_date_to = end.strftime("%Y-%m-%d")

# --- 9. API CALL: OF period OF date ---
params = [
    ("period_step", "day"),
    ("source", "shops")
]

if period_option == "date":
    params.append(("period", "date"))
    params.extend([("form_date_from", form_date_from), ("form_date_to", form_date_to)])
else:
    params.append(("period", period_option))

for sid in shop_ids:
    params.append(("data[]", sid))
for output in ["count_in", "conversion_rate", "turnover", "sales_per_visitor"]:
    params.append(("data_output[]", output))

query_string = urlencode(params, doseq=True, safe='[]')
url = f"{API_BASE}/get-report?{query_string}"
data_response = requests.get(url)

# --- ERROR HANDLING ---
st.write(f"DEBUG: HTTP Status = {data_response.status_code}")
st.subheader("DEBUG: API URL")
st.code(url, language="text")

if data_response.status_code != 200:
    st.error(f"API fout: {data_response.status_code}")
    st.code(data_response.text[:500], language="text")
    st.stop()

try:
    raw_json = data_response.json()
except requests.exceptions.JSONDecodeError:
    st.error("**JSON fout:** API gaf geen geldige JSON. Controleer datums.")
    st.code(data_response.text[:1000], language="html")
    st.stop()

st.subheader("DEBUG: Raw JSON (van API)")
st.json(raw_json, expanded=False)

# --- 10. DEBUG ---
st.subheader("DEBUG: API URL")
st.code(url, language="text")
st.subheader("DEBUG: Raw JSON (van API)")
st.json(raw_json, expanded=False)

# --- 11. NORMALISEER ---
df_raw = normalize_vemcount_response(raw_json)
st.write(f"DEBUG: df_raw.shape = {df_raw.shape}")

if df_raw.empty:
    st.error(f"Geen data voor {period_option}. API gaf lege response.")
    st.stop()

df_raw["name"] = df_raw["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")

# --- 12. DEBUG TABEL ---
st.subheader("DEBUG: Raw Data (ALLE DAGEN)")
st.dataframe(df_raw[["date", "name", "count_in", "conversion_rate", "turnover", "sales_per_visitor"]])

# --- 13. AGGREGEER ---
df = df_raw.copy()
multi_day_periods = fixed_periods + ["custom"]
if period_option in multi_day_periods and len(df) > 1:
    agg = df.groupby("shop_id").agg({
        "count_in": "sum",
        "turnover": "sum",
        "conversion_rate": "mean",
        "sales_per_visitor": "mean"
    }).reset_index()
    agg["name"] = agg["shop_id"].map({loc["id"]: loc["name"] for loc in locations}).fillna("Onbekend")
    df = agg

# --- 14. ROL ---
role = st.selectbox("Rol", ["Store Manager", "Regio Manager", "Directie"])

# --- 15. UI ---
st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown(f"**{client['name']}** – *Mark Ryski*")

if role == "Store Manager" and len(selected) == 1:
    row = df.iloc[0]
    period_display = "custom" if period_option == "custom" else period_option.capitalize()
    st.header(f"{row['name']} – {period_display}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Footfall", f"{int(row['count_in']):,}", "", "primary")
    with c2: kpi_card("Conversie", f"{row['conversion_rate']:.1f}%", "", "good" if row['conversion_rate'] >= 25 else "bad")
    with c3: kpi_card("Omzet", f"€{int(row['turnover']):,}", "", "good")
    with c4: kpi_card("SPV", f"€{row['sales_per_visitor']:.2f}", "", "neutral")

    # --- GRAFIEK ---
    st.subheader("Trend: Footfall & Conversie per dag")
    chart_data = df_raw[["date", "count_in", "conversion_rate"]].copy()
    chart_data["date"] = pd.to_datetime(chart_data["date"], format="%a. %b %d, %Y")
    chart_data = chart_data.sort_values("date")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart(chart_data.set_index("date")["count_in"], use_container_width=True)
        st.caption("Footfall per dag")
    with col2:
        st.line_chart(chart_data.set_index("date")["conversion_rate"], use_container_width=True)
        st.caption("Conversie % per dag")

    # --- AI-ACTIE ---
    footfall = int(row["count_in"])
    conv = row["conversion_rate"]
    spv = row["sales_per_visitor"]
    if footfall == 0:
        st.warning("**AI Alert:** Geen traffic. Controleer sensoren of openingstijden.")
    elif conv < 12:
        st.warning(f"**AI Actie:** Conversie laag ({conv:.1f}%). +1 FTE piekuren → +3-5% conversie.")
    elif spv < 2.5:
        st.info(f"**AI Tip:** SPV laag (€{spv:.2f}). Train upselling.")
    else:
        st.success("**AI Goed:** Sterke week! Focus op loyaliteit.")

elif role == "Regio Manager":
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

st.caption("RetailGift AI: `period` of `custom` – nooit beide. 100% schoon.")
