from modules.carbon.calculator import estimate_route_carbon
from modules.routing.optimizer import haversine_km, validate_weights, optimize_routes
from modules.hub_risk.analyzer import analyze_hub
from modules.delivery_risk.features import fallback_delay, fallback_sla_probability, risk_level
from modules.loading.analyzer import demo_detections
from modules.maintenance.rules import maintenance_score


def test_carbon_baseline():
    result = estimate_route_carbon(20, 300, 900, 10, "diesel")
    assert result["fuel_liter"] == 2
    assert result["co2_kg"] > 5


def test_haversine_symmetry():
    a = (-6.2, 106.8); b = (-6.3, 107.0)
    assert round(haversine_km(a, b), 5) == round(haversine_km(b, a), 5)
    assert haversine_km(a, a) == 0


def test_weight_validation():
    validate_weights({"time": .3, "fuel": .2, "co2": .2, "sla": .3})


def test_loading_demo_is_deterministic():
    first = demo_detections(b"abc")
    second = demo_detections(b"abc")
    assert first["image_hash"] == second["image_hash"]
    assert first["is_demo"] is True


def test_hub_critical_score():
    hub = {"hub_id":"HUB-BKS","normal_dwell_time_min":35}
    event = {"arrival_rate_per_hour":40,"departure_rate_per_hour":15,"queue_size":42,"average_dwell_time_min":90,"processing_rate_per_hour":24,"sorting_time_min":60,"loading_time_min":36,"unloading_time_min":28,"current_delayed_shipments":31,"current_total_shipments":90}
    result = analyze_hub(event, hub)
    assert result["risk_level"] == "Critical"
    assert result["likely_bottleneck"] in result["bottleneck_evidence"]


def test_delivery_risk_thresholds():
    features = {"traffic_index": .9, "weather_severity": .8, "hub_dwell_excess": 50, "sla_buffer_minutes": -15, "loading_compliance_score": 70, "priority_score": .7, "rainfall_mm": 18}
    delay = fallback_delay(features)
    prob = fallback_sla_probability(features, delay)
    assert delay > 40
    assert risk_level(prob) in {"High", "Critical"}


def test_maintenance_rules_high_risk():
    result = maintenance_score({"current_km": 20000, "last_service_km": 12000, "last_service_date": "2025-01-01"}, [{"x": 1}])
    assert result["risk_level"] in {"Check-Up Soon", "Service Recommended"}


def test_route_optimizer_visits_stops_once():
    shipment = {"shipment_id":"S","load_weight_kg":100,"load_volume_liter":100,"planned_travel_time_min":50}
    vehicle = {"capacity_weight_kg":500,"capacity_volume_liter":1000,"fuel_efficiency_km_per_liter":12,"fuel_type":"diesel"}
    stops = [
        {"stop_id":"D","lat":0,"lon":0,"risk_hint":.1},
        {"stop_id":"A","lat":0.1,"lon":0.1,"risk_hint":.2},
        {"stop_id":"B","lat":0.2,"lon":0.1,"risk_hint":.3},
        {"stop_id":"C","lat":0.1,"lon":0.2,"risk_hint":.4},
    ]
    result = optimize_routes(shipment, vehicle, stops, .4, .1, .2)
    for candidate in result["candidates"]:
        middle = candidate["sequence"][1:-1]
        assert sorted(middle) == ["A", "B", "C"]
