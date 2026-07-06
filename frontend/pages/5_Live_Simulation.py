import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Live Simulation")
header("Live Simulation", "Advance simulated near-real-time events and watch rescoring, alerts, and routing update.")

c1,c2,c3,c4 = st.columns(4)
with c1:
    if st.button("Reset"): st.session_state["sim"] = api.simulation_reset()
with c2:
    if st.button("Next Event", type="primary"): st.session_state["sim"] = api.simulation_next()
with c3:
    if st.button("Auto Play"): st.session_state["sim"] = api.simulation_play()
with c4:
    if st.button("Pause"): st.session_state["sim"] = api.simulation_pause()
st.json(st.session_state.get("sim", api.simulation_state()))
