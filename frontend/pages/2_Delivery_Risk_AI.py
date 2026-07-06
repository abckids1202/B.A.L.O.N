import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Delivery Risk AI")
header("Delivery Risk AI", "Predict delay and SLA breach risk from current shipment conditions.")

shipments = api.list_shipments()
ids = [s["shipment_id"] for s in shipments] if isinstance(shipments, list) else []
sid = st.selectbox("Shipment", ids, index=ids.index("SHP-1028") if "SHP-1028" in ids else 0)
upload = st.file_uploader("Loading image", type=["jpg","jpeg","png"])
if upload and st.button("Run Loading Analysis", type="primary"):
    st.json(api.analyze_loading(sid, upload))
if st.button("Run Risk Prediction", type="primary"):
    st.session_state["risk"] = api.predict_risk(sid)
if "risk" in st.session_state:
    st.json(st.session_state["risk"])
st.subheader("Prediction history")
st.json(api.risk_history(sid))
