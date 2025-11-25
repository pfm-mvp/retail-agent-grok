# pages/Home.py – JOUW MOOIE THUISSCREEN – 1 APP, 3 TOOLS
import streamlit as st

st.set_page_config(page_title="RetailGift AI", layout="centered")

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🛍️ Store Manager\n\nDagelijkse operatie + weer + voorspelling", use_container_width=True):
        st.switch_page("pages/retailgift_store.py")

with col2:
    if st.button("🔥 Regio Manager\n\nStoplichten, hotspot, CBS, potentieel", use_container_width=True):
        st.switch_page("pages/retailgift_regio.py")

with col3:
    if st.button("📊 Directie\n\nPortfolio, scenario's, Q4 forecast (binnenkort)", use_container_width=True):
        st.info("Directie dashboard komt binnen 48 uur live")

st.markdown("---")
st.caption("RetailGift AI – 1 app, 3 niveaus – LIVE & PERFECT – 25 nov 2025")
