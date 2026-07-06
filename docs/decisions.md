# Technical Decisions

- The MVP keeps Streamlit as a thin HTTP client and puts all business behavior behind FastAPI.
- Route distance uses Haversine-derived approximations and is labeled as simplified.
- Missing YOLO weights use deterministic Demo Detection Mode with explicit disclosure.
- Maintenance remains rule-based because validated mechanical failure labels are outside MVP scope.
