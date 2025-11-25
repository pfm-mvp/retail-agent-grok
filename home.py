# home.py – DEFINITIEF WERKENDE VERSIE (25 nov 2025)
import streamlit as st
import requests
from datetime import date, timedelta

st.set_page_config(page_title="RetailGift AI", layout="centered")

API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

clients = requests.get(CLIENTS_JSON).json()

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw dashboard")

client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
client_id = client["company_id"]
locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

period_option = st.selectbox("Periode", [
    "this_month", "last_month", "this_week", "last_week", "yesterday", "date"
], index=0)

form_date_from = form_date_to = None
if period_option == "date":
    c1, c2 = st.columns(2)
    with c1: start = st.date_input("Van", date.today() - timedelta(days=30))
    with c2: end = st.date_input("Tot", date.today())
    if start <= end:
        form_date_from = start.strftime("%Y-%m-%d")
        form_date_to = end.strftime("%Y-%m-%d")

# --- STORE MANAGER ---
if st.button("🛍️ Store Manager – Kies 1 vestiging", type="primary"):
    selected = st.multiselect("Kies precies 1 vestiging", locations, format_func=lambda x: x["name"], max_selections=1)
    if len(selected) == 1:
        st.session_state.update({
            "selected_shop_ids": [selected[0]["id"]],
            "client_id": client_id,
            "locations": locations,
            "period_option": period_option,
            "form_date_from": form_date_from,
            "form_date_to": form_date_to
        })
        st.switch_page("pages/retailgift_store.py")
    else:
        st.warning("Kies precies 1 vestiging")

# --- REGIO MANAGER (alle winkels direct) ---
if st.button("🔥 Regio Manager – Alle vestigingen"):
    st.session_state.update({
        "selected_shop_ids": [loc["id"] for loc in locations],
        "client_id": client_id,
        "locations": locations,
        "period_option": period_option,
        "form_date_from": form_date_from,
        "form_date_to": form_date_to
    })
    st.switch_page("pages/retailgift_regio.py")

st.caption("RetailGift AI – 100% STABIEL – 25 nov 2025")
