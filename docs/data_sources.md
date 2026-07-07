# Data Sources

## Traffic
Training: historical route/traffic observations. Runtime: Google Routes or TomTom. Current: DemoTrafficProvider.

## Weather
Training: historical weather archive. Runtime: BMKG or OpenWeather. Current: DemoWeatherProvider.

## GPS
Training/runtime future: driver app or IoT tracker. Current: DemoGPSProvider.

## Shipment / ERP
Training/runtime future: ERP/TMS shipment records. Current: DemoShipmentProvider over SQLite synthetic data.

## Hub
Training/runtime future: WMS and hub scan logs. Current: DemoHubProvider.

## Vehicle
Training/runtime future: fleet system and service records. Current: DemoVehicleProvider.

## YOLO
Training future: team-collected annotated package/loading images. Runtime: camera upload. Current: deterministic demo mode.

## Carbon
Activity data: distance, fuel, load, vehicle. Factors should be versioned in configuration. Current: deterministic prototype factors.
