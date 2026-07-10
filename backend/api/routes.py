from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.api import CarbonEstimateRequest, RouteOptimizeRequest
from backend.services import core


router = APIRouter(prefix="/api")


def handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/vehicles")
def vehicles():
    return core.list_vehicles()


@router.get("/vehicles/paged")
def vehicles_paged(page: int = 1, page_size: int = 50, status: str | None = None):
    return core.paged_vehicles(page=page, page_size=page_size, status=status)


@router.get("/drivers")
def drivers(page: int = 1, page_size: int = 50):
    return core.list_drivers(page=page, page_size=page_size)


@router.get("/shipments")
def shipments():
    return core.list_shipments()


@router.get("/shipments/paged")
def shipments_paged(page: int = 1, page_size: int = 50, status: str | None = None, q: str | None = None):
    return core.paged_shipments(page=page, page_size=page_size, status=status, q=q)


@router.get("/network/summary")
def network_summary():
    return core.synthetic_network_summary()

@router.get("/packages/{shipment_id}/journey-view")
def package_journey_view(shipment_id: str):
    return handle(core.package_journey_view, shipment_id)

@router.get("/packages/{shipment_id}/digital-twin")
def package_digital_twin(shipment_id: str):
    return handle(core.shipment_digital_twin, shipment_id)


@router.get("/interventions")
def interventions(status: str | None = None, shipment_id: str | None = None):
    return core.list_interventions(status=status, shipment_id=shipment_id)


@router.get("/interventions/{intervention_id}")
def intervention_detail(intervention_id: str):
    return handle(core.get_intervention, intervention_id)


@router.post("/interventions/{intervention_id}/accept")
def intervention_accept(intervention_id: str):
    return handle(core.accept_intervention, intervention_id)


@router.post("/interventions/{intervention_id}/reject")
def intervention_reject(intervention_id: str, reason: str = "Rejected by operator"):
    return handle(core.reject_intervention, intervention_id, reason)


@router.get("/interventions/{intervention_id}/impact")
def intervention_impact(intervention_id: str):
    return handle(core.intervention_impact, intervention_id)


@router.get("/hubs")
def hubs():
    return core.list_hubs()


@router.post("/loading/analyze")
async def loading_analyze(shipment_id: str, file: UploadFile = File(...)):
    return handle(core.analyze_loading, shipment_id, file.filename or "upload.png", await file.read())


@router.get("/loading/history/{shipment_id}")
def loading_history(shipment_id: str):
    return core.loading_history(shipment_id)


@router.get("/operational-signals")
def operational_signals(entity_id: str | None = None, signal_type: str | None = None):
    return core.list_operational_signals(entity_id=entity_id, signal_type=signal_type)


@router.post("/vision/package-damage")
async def package_damage_signal(shipment_id: str, file: UploadFile | None = File(None)):
    content = await file.read() if file else None
    filename = file.filename if file and file.filename else "demo-damage.jpg"
    return handle(core.process_package_damage_signal, shipment_id, filename, content)


@router.post("/vision/hub-occupancy/{hub_id}")
def hub_occupancy_signal(hub_id: str, area: str = "sorting", observed_packages: int | None = None):
    return handle(core.process_hub_occupancy_signal, hub_id, area, observed_packages)


@router.post("/forecast/hub-overflow/{hub_id}")
def hub_overflow_signal(hub_id: str, horizon_minutes: int = 90):
    return handle(core.forecast_hub_overflow_signal, hub_id, horizon_minutes)


@router.post("/vision/loading-validation")
def loading_validation_signal(shipment_id: str, observed_vehicle_id: str | None = None):
    return handle(core.process_wrong_loading_signal, shipment_id, observed_vehicle_id)


@router.post("/vision/demo-scenario")
def visual_demo_scenario():
    return core.run_visual_demo_scenario()


@router.post("/risk/predict/{shipment_id}")
def risk_predict(shipment_id: str):
    return handle(core.predict_risk, shipment_id)


@router.post("/risk/predict-batch")
def risk_batch():
    return core.predict_batch()


@router.get("/risk/history/{shipment_id}")
def risk_history(shipment_id: str):
    return core.risk_history(shipment_id)


@router.post("/routes/optimize")
def routes_optimize(req: RouteOptimizeRequest):
    return handle(core.optimize, req.model_dump())


@router.post("/routes/reoptimize")
def routes_reoptimize(req: RouteOptimizeRequest):
    return handle(core.optimize, req.model_dump())


@router.get("/routes/{shipment_id}/candidates")
def routes_candidates(shipment_id: str):
    return core.route_candidates(shipment_id)


@router.post("/routes/recommend")
def routes_recommend(req: RouteOptimizeRequest):
    return handle(core.optimize, req.model_dump())


@router.post("/carbon/estimate")
def carbon_estimate(req: CarbonEstimateRequest):
    return handle(core.carbon_estimate, req.model_dump())


@router.post("/hubs/analyze/{hub_id}")
def hub_analyze(hub_id: str):
    return handle(core.analyze_hub_service, hub_id)


@router.get("/hubs/risk")
def hubs_risk():
    return core.all_hub_risk()


@router.get("/hubs/{hub_id}/history")
def hubs_history(hub_id: str):
    return core.hub_history(hub_id)


@router.post("/fleet/analyze")
def fleet_analyze():
    return core.fleet_analysis()


@router.post("/maintenance/analyze/{vehicle_id}")
def maintenance_analyze(vehicle_id: str):
    return handle(core.maintenance_analysis, vehicle_id)


@router.get("/alerts")
def alerts():
    return core.alerts()


@router.patch("/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str):
    return core.acknowledge_alert(alert_id)


@router.post("/simulation/reset")
def simulation_reset():
    return core.simulation_reset()


@router.post("/simulation/next")
def simulation_next():
    return core.simulation_next()


@router.post("/simulation/play")
def simulation_play():
    return core.simulation_play()


@router.post("/simulation/pause")
def simulation_pause():
    return core.simulation_pause()


@router.get("/simulation/state")
def simulation_state():
    return core.simulation_state()


@router.get("/analytics/summary")
def analytics_summary():
    return core.analytics_summary()


@router.get("/models")
def models():
    return core.models()


@router.get("/reports/executive-summary")
def executive_summary():
    return core.executive_summary()
@router.get("/providers/status")
def providers_status():
    return core.provider_status()


@router.get("/snapshots/{shipment_id}/current")
def current_snapshot(shipment_id: str):
    return handle(core.operational_snapshot, shipment_id)


@router.get("/data-sources")
def data_sources():
    return core.data_sources()


@router.get("/training-data/status")
def training_data_status():
    return core.training_data_status()
