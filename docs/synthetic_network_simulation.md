# Synthetic Network Simulation

The default seed now builds the `COMPACT_PRESENTATION` preset: 500 unique shipments, 12 Jabodetabek logistics nodes, 60 vehicles, 50 drivers, 40 route recommendation jobs, and thousands of correlated operational context records across traffic, weather, GPS, hub events, route recommendations, and the hero `SHP-1028` live replay.

The generator is deterministic (`seed=42`) and keeps one row per shipment. Current stage, SLA pressure, delay, route distance, carbon, vehicle assignment, hub dwell, and ETA are derived from geography, vehicle type, load, traffic, weather, and hub context rather than cloned shipment families.

## Presets

- `COMPACT_PRESENTATION`: default competition dataset.
- `LARGE_DEMO_NETWORK`: available in the generator for larger local experiments.
- `STRESS_DEVELOPMENT`: configurable stress profile; use for query and pagination testing, not presentation.

## Commands

```bash
python scripts/generate_demo_data.py
python scripts/generate_demo_data.py --preset LARGE_DEMO_NETWORK
```

## Scale-Safe APIs

- `GET /api/network/summary`
- `GET /api/shipments/paged?page=1&page_size=60`
- `GET /api/vehicles/paged?page=1&page_size=60`
- `GET /api/drivers?page=1&page_size=50`

The React frontend uses paged shipment and vehicle reads for initial bootstrap and Package Tracking so it does not render every entity at once.
