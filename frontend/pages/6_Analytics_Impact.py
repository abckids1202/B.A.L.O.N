import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Analytics & Impact")
header("Analytics & Impact", "Inspect computed distance, fuel, carbon, SLA, and fleet impact assumptions.")
st.json(api.analytics_summary())
