# home.py – WELKOM + 1 KLIK NAAR JOUW TOOL
import streamlit as st

st.set_page_config(page_title="RetailGift AI", layout="centered")

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw dashboard")

col1, col2 = st.columns(2)

with col1:
    if st.button("🛍️ Store Manager\nDagverkoop • Weer • Realistische voorspelling", use_container_width=True, type="primary"):
        st.switch_page("pages/retailgift_store.py")

with col2:
    if st.button("🔥 Regio Manager\nAlle winkels • Stoplichten • AI • CBS • Potentieel", use_container_width=True):
        st.switch_page("pages/retailgift_regio.py")

st.info("Directie dashboard komt volgende week")
st.caption("RetailGift AI – FINAL & PRESENTATIE-KLAAR – 25 nov 2025")
