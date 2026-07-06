import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Network Resilience")
header("Network Resilience", "Detect hub bottlenecks, fleet utilization patterns, and check-up needs.")

hubs = api.list_hubs(); vehicles = api.list_vehicles()
hid = st.selectbox("Hub", [h["hub_id"] for h in hubs])
if st.button("Analyze Hub", type="primary"):
    st.json(api.analyze_hub(hid))
st.subheader("All hub risk")
st.dataframe(api.hubs_risk(), use_container_width=True)
st.subheader("Fleet utilization")
st.json(api.analyze_fleet())
vid = st.selectbox("Maintenance vehicle", [v["vehicle_id"] for v in vehicles])
if st.button("Analyze Maintenance"):
    st.json(api.analyze_maintenance(vid))
