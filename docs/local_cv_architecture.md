# Local CV Architecture

The local CV worker is a sensor layer. It opens the camera once, discovers package and damage assets once, then sends normalized material events to the existing FastAPI backend. The backend remains the decision brain and updates digital twins, SLA forecasts, hub state, interventions, and analytics.
