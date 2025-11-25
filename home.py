# home.py – 100% WERKENDE THUISSCREEN + DOORGEVEN KEUZES
import streamlit as st
import requests

st.set_page_config(page_title="RetailGift AI", layout="centered", initial_sidebar_state="collapsed")

# --- SECRETS ---
API_BASE = st.secrets["API_URL"].rstrip("/")
CLIENTS_JSON = st.secrets["clients_json_url"]

# --- LAAD KLANTEN ---
clients = requests.get(CLIENTS_JSON).json()

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw dashboard")

# --- INPUTS ---
col1, col2 = st.columns([1, 1])

with col1:
    client = st.selectbox("Klant", clients, format_func=lambda x: f"{x['name']} ({x['brand']})")
    client_id = client["company_id"]

    locations = requests.get(f"{API_BASE}/clients/{client_id}/locations").json()["data"]
    selected_locations = st.multiselect("Vestiging(en)", locations, format_func=lambda x: x["name"], default=locations[:1])

with col2:
    period_option = st.selectbox("Periode", [
        "yesterday", "today", "this_week", "last_week",
        "this_month", "last_month", "date"
    ], index=4)

    form_date_from = form_date_to = None
    if period_option == "date":
        start = st.date_input("Van", date.today() - timedelta(days=7))
        end = st.date_input("Tot", date.today())
        if start <= end:
            form_date_from = start.strftime("%Y-%m-%d")
            form_date_to = end.strftime("%Y-%m-%d")
        else:
            st.error("Van-datum moet vóór Tot-datum zijn")
            st.stop()

# --- OPSLAAN IN SESSION STATE ---
if st.button("Ga naar Store Manager", type="primary", use_container_width=True):
    st.session_state.selected_shop_ids = [loc["id"] for loc in selected_locations]
    st.session_state.client_id = client_id
    st.session_state.locations = locations
    st.session_state.period_option = period_option
    st.session_state.form_date_from = form_date_from
    st.session_state.form_date_to = form_date_to
    st.switch_page("pages/retailgift_store.py")

if st.button("Ga naar Regio Manager", use_container_width=True):
    st.session_state.selected_shop_ids = [loc["id"] for loc in selected_locations]
    st.session_state.client_id = client_id
    st.session_state.locations = locations
    st.session_state.period_option = period_option
    st.session_state.form_date_from = form_date_from
    st.session_state.form_date_to = form_date_to
    st.switch_page("pages/retailgift_regio.py")

st.info("Directie dashboard komt binnen 24 uur")
st.caption("RetailGift AI – 1 app, 3 niveaus – 100% STABIEL – 25 nov 2025")
