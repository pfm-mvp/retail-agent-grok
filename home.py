# home.py – JOUW PERFECTE THUISSCREEN (WERKT ALTIJD)
import streamlit as st

st.set_page_config(page_title="RetailGift AI", layout="centered", initial_sidebar_state="collapsed")

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw niveau")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🛍️ **Store Manager**\n\nDagelijkse operatie + weer + voorspelling", use_container_width=True, type="primary"):
        st.switch_page("pages/retailgift_store.py")

with col2:
    if st.button("🔥 **Regio Manager**\n\nStoplichten • Hotspot • CBS • Potentieel", use_container_width=True):
        st.switch_page("pages/retailgift_regio.py")

with col3:
    if st.button("📊 **Directie**\n\nPortfolio • Scenario's • Q4 forecast", use_container_width=True):
        st.info("Directie dashboard komt binnen 24 uur live")

st.markdown("---")
st.caption("RetailGift AI – 1 app, 3 niveaus – 100% STABIEL – 25 nov 2025")
