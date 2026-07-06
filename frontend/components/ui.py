import streamlit as st


def setup_page(title="LogiSense AI"):
    st.set_page_config(page_title=title, layout="wide")
    st.markdown('''
    <style>
    .stApp { background: #F4F7FB; color: #0F172A; font-family: Inter, Segoe UI, Arial, sans-serif; }
    [data-testid="stSidebar"] { background: #0F172A; }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; background:#6D28D9; color:white; }
    .card { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:16px; box-shadow:0 1px 3px rgba(15,23,42,.08); }
    .metric-label { color:#64748B; font-size:12px; font-weight:700; }
    .metric-value { font-size:30px; font-weight:750; color:#0F172A; }
    </style>
    ''', unsafe_allow_html=True)


def header(title, description):
    st.title(title)
    st.caption(description)
    st.markdown('<span class="badge">SYNTHETIC DEMO ENVIRONMENT</span>', unsafe_allow_html=True)


def metric_card(label, value, context=""):
    st.markdown(f'<div class="card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div>{context}</div></div>', unsafe_allow_html=True)
