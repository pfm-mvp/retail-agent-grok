# home.py – PERFECTE THUISSCREEN (Regio Manager = alle winkels automatisch)
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

col1, col2 = st.columns(2)

with col1:
    client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
    client_id = client["company_id"]
    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]

with col2:
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

# --- STORE MANAGER (1 winkel kiezen) ---
if st.button("🛍️ Store Manager – 1 vestiging", type="primary", use_container_width=True):
    selected = st.multiselect("Kies 1 vestiging", locations, format_func=lambda x: x["name"], max_selections=1)
    if len(selected) != 1:
        st.error("Kies precies 1 vestiging")
    else:
        st.session_state.update({
            "selected_shop_ids": [selected[0]["id"]],
            "client_id": client_id,
            "locations": locations,
            "period_option": period_option,
            "form_date_from": form_date_from,
            "form_date_to": form_date_to
        })
        st.switch_page("pages/retailgift_store.py")

# --- REGIO MANAGER (alle winkels automatisch!) ---
if st.button("🔥 Regio Manager – Alle vestigingen direct", use_container_width=True):
    st.session_state.update({
        "selected_shop_ids": [loc["id"] for loc in locations],
        "client_id": client_id,
        "locations": locations,
        "period_option": period_option,
        "form_date_from": form_date_from,
        "form_date_to": form_date_to
    })
    st.switch_page("pages/retailgift_regio.py")

st.info("Directie dashboard komt morgen")
st.caption("RetailGift AI – PERFECTE FLOW – 25 nov 2025")
