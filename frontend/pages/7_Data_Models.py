import streamlit as st
from components.ui import setup_page, header
import api_client as api

setup_page("Data & Models")
header("Data & Models", "Review data provenance, synthetic labels, model metrics, availability, and limitations.")
st.dataframe(api.models(), use_container_width=True)
st.info('Prototype models may be trained on synthetic logistics labels and are not field-validated production metrics.')
