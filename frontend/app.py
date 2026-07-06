import streamlit as st
import plotly.express as px
from components.ui import setup_page, header, metric_card
import api_client as api

setup_page()
header("LogiSense AI", "Green & Resilient Logistics Command Center")

summary = api.analytics_summary()
if "error" in summary:
    st.error("Backend unavailable. Start FastAPI with: uvicorn backend.main:app --reload")
    st.json(summary)
    st.stop()

c1, c2, c3, c4, c5 = st.columns(5)
with c1: metric_card("Active shipments", summary["active_shipments"])
with c2: metric_card("Delayed risk", summary["predicted_delayed_shipments"])
with c3: metric_card("Critical hubs", summary["critical_hub_count"])
with c4: metric_card("CO2 today", f"{summary['daily_carbon_estimate_kg']} kg")
with c5: metric_card("Fleet utilization", f"{summary['fleet_utilization']['fleet_utilization_score']}%")

left, right = st.columns([2, 1])
with left:
    dist = summary["risk_distribution"]
    st.plotly_chart(px.bar(x=list(dist.keys()), y=list(dist.values()), labels={"x":"SLA risk", "y":"Shipments"}, title="SLA risk distribution"), use_container_width=True)
with right:
    st.subheader("Critical alerts")
    for alert in summary["alerts"]:
        st.warning(f"{alert['severity']}: {alert['title']} - {alert['message']}")

st.subheader("Route impact")
st.json(summary["route_impact"])
