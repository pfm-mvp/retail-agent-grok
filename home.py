import streamlit as st

st.set_page_config(page_title="RetailGift AI", layout="centered")

st.image("https://i.imgur.com/8Y5fX5P.png", width=300)
st.title("STORE TRAFFIC IS A GIFT")
st.markdown("### Kies jouw dashboard")

col1, col2 = st.columns(2)
with col1:
    if st.button("🛍️ Store Manager", use_container_width=True, type="primary"):
        st.switch_page("pages/retailgift_store.py")
with col2:
    if st.button("🔥 Regio Manager", use_container_width=True):
        st.switch_page("pages/retailgift_regio.py")

st.caption("RetailGift AI – 100% WERKENDE DEMO – 25 nov 2025")
