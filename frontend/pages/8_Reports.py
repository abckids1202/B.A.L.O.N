import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Reports")
header("Reports", "Generate executive, shipment, route, hub, and alert summaries for export.")

report = api.executive_summary()
st.json(report)
st.download_button("Export JSON", data=str(report), file_name="logisense_executive_summary.json", mime="application/json")
