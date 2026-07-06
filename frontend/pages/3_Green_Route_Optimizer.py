import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Green Route Optimizer")
header("Green Route Optimizer", "Compare route candidates across time, fuel, carbon, and SLA risk.")

shipments = api.list_shipments(); vehicles = api.list_vehicles()
sid = st.selectbox("Shipment", [s["shipment_id"] for s in shipments])
vid = st.selectbox("Vehicle", [v["vehicle_id"] for v in vehicles])
preset = st.selectbox("Decision preset", ["balanced_ai","fastest","greenest","sla_priority"])
if st.button("Optimize Routes", type="primary"):
    st.session_state["routes"] = api.optimize_routes({"shipment_id": sid, "vehicle_id": vid, "preset": preset})
if "routes" in st.session_state:
    st.success(st.session_state["routes"]["explanation"])
    st.dataframe([{**c["metrics"], "candidate": c["candidate_name"]} for c in st.session_state["routes"]["candidates"]], use_container_width=True)
