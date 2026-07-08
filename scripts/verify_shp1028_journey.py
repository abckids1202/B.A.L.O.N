from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services import core


def main() -> None:
    result = core.simulation_reset()
    view = result["journey_view"]
    print("RESET", view["current_state"]["stage"], view["current_state"]["location_id"])
    seen = []
    while True:
        result = core.simulation_next()
        if result.get("complete"):
            break
        event = result["processed_event"]
        view = result["journey_view"]
        risk = view["latest_risk"]
        current = view["latest_operational_snapshot"]
        seen.append(event["event_id"])
        print(
            event["event_id"],
            event["event_type"],
            view["current_state"]["stage"],
            view["current_state"]["location_id"],
            "delay=", risk["predicted_delay_minutes"],
            "sla=", risk["sla_probability"],
            "traffic=", current["traffic_index"],
            "weather=", current["weather_severity"],
            "interventions=", len(view.get("active_interventions", [])),
            "events=", len(view["timeline"]),
        )
    final_view = core.package_journey_view("SHP-1028")
    assert seen, "No demo events processed"
    assert final_view["current_state"]["stage"] == "DELIVERED"
    assert final_view["current_state"]["status"] == "DELIVERED"
    assert len(final_view["timeline"]) >= len(seen)
    assert final_view.get("active_interventions"), "Expected at least one operational intervention"
    print("verify_shp1028_journey: OK", {"events": len(seen), "final_stage": final_view["current_state"]["stage"], "interventions": len(final_view.get("active_interventions", []))})


if __name__ == "__main__":
    main()
