# Data Source Strategy

B.A.L.O.N separates data into four categories.

| Category | Meaning | Examples |
|---|---|---|
| A Model Training Data | Historical data used to fit models | delay snapshots, SLA labels, carbon formula targets, annotated YOLO images |
| B Runtime Operational Data | Near-real-time state used by the app | traffic, weather, GPS, hub events |
| C Master Business Data | Relatively static entity data | shipments, vehicles, hubs, routes |
| D Derived B.A.L.O.N Data | System outputs | predictions, alerts, route recommendations, carbon estimates |

| Domain | Field | Category | Training/Runtime Use | Preferred Real Source | Prototype Source | Freshness | Units | Nullable | Provenance Field |
|---|---|---|---|---|---|---|---|---|---|
| Traffic | traffic_index | B | Runtime feature | Google Routes / TomTom | DemoTrafficProvider | minutes | 0-1 index | no | traffic.provider |
| Weather | rainfall_mm | B | Runtime feature | BMKG / OpenWeather | DemoWeatherProvider | hourly | mm | no | weather.provider |
| GPS | speed_kmh | B | Runtime feature | Driver app / IoT | DemoGPSProvider | seconds-minutes | km/h | no | gps.provider |
| Shipment | sla_deadline | C | Master + feature | ERP/TMS | SQLite demo shipment | per shipment | ISO time | no | shipment provider |
| Hub | average_dwell_time_min | B | Runtime feature | WMS / hub scan logs | DemoHubProvider | minutes | minutes | no | hub_event.provider |
| Delay | predicted_delay_minutes | D | Derived output | B.A.L.O.N delay model | Runtime model/fallback | on scoring | minutes | no | model_source |
