from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from database import repositories as repo

from backend.schemas.api import CarbonEstimateRequest, RouteOptimizeRequest
from backend.services import core, web_cv


router = APIRouter(prefix="/api")


def handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


async def handle_async(fn, *args, **kwargs):
    try:
        return await fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        code = str(exc)
        status = 503 if code in {"CV_INFERENCE_BUSY", "INFERENCE_TIMEOUT"} else 500
        raise HTTPException(status_code=status, detail=code)


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


@router.get("/clock")
def clock():
    return core.clock_state()

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


@router.get("/visual-intelligence/assets")
def visual_intelligence_assets():
    return core.visual_asset_audit()


@router.get("/visual-intelligence/summary")
def visual_intelligence_summary():
    return core.visual_intelligence_summary()


@router.get("/visual-intelligence/qr-identity/{shipment_id}")
def visual_intelligence_qr_identity(shipment_id: str):
    return handle(core.package_qr_identity_context, shipment_id)


@router.post("/visual-intelligence/package-quality")
def visual_intelligence_package_quality(shipment_id: str = "SHP-1028"):
    return handle(core.run_package_quality_workflow, shipment_id)


@router.post("/visual-intelligence/dispatch-validation")
def visual_intelligence_dispatch_validation(shipment_id: str = "SHP-1028", observed_vehicle_id: str | None = "VAN-044"):
    return handle(core.run_dispatch_validation_workflow, shipment_id, observed_vehicle_id)


@router.post("/visual-intelligence/loading-compliance")
def visual_intelligence_loading_compliance(vehicle_id: str = "TRK-001", loaded_packages: int = 6, visual_capacity: int = 5):
    return handle(core.run_loading_compliance_workflow, vehicle_id, loaded_packages, visual_capacity)


@router.post("/visual-intelligence/hub-vision")
def visual_intelligence_hub_vision(hub_id: str = "HUB-JKT", observed_packages: int | None = None):
    return handle(core.run_hub_vision_workflow, hub_id, observed_packages)


@router.post("/cv/events")
def cv_event_ingest(event: dict = Body(...)):
    return handle(core.ingest_cv_event, event)


@router.get("/cv/state")
def cv_state():
    return core.cv_state()


@router.get("/cv/events")
def cv_events(limit: int = 80):
    return core.cv_events(limit)


@router.get("/cv/demo-packages/{shipment_id}")
def cv_demo_package(shipment_id: str):
    return handle(core.cv_demo_package_lookup, shipment_id)


@router.get("/cv/events/stream")
async def cv_event_stream():
    async def events():
        last_id = None
        while True:
            state = core.cv_state()
            latest = state.get("latest_event")
            if latest and latest.get("event_id") != last_id:
                last_id = latest["event_id"]
                yield f"event: cv_event\ndata: {repo.jdump(latest)}\n\n"
            else:
                yield f"event: heartbeat\ndata: {repo.jdump({'status': 'ok', 'time': core.now_iso()})}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


@router.get("/cv/events/{event_id}")
def cv_event(event_id: str):
    return handle(core.cv_event, event_id)


@router.post("/cv/demo-replay")
def cv_demo_replay(scenario: str = "ALL"):
    return handle(core.replay_cv_scenario, scenario)


@router.get("/web-cv/health")
def web_cv_health():
    return web_cv.health()


@router.get("/web-cv/models/status")
def web_cv_model_status():
    return web_cv.model_status()


@router.post("/web-cv/sessions")
def web_cv_create_session(payload: dict = Body(...)):
    return handle(web_cv.create_session, payload.get("module"), payload.get("processing_mode", "LIVE_CAMERA"))


@router.get("/web-cv/sessions/{session_id}")
def web_cv_get_session(session_id: str):
    return handle(web_cv.get_session, session_id)


@router.post("/web-cv/sessions/{session_id}/reset")
def web_cv_reset_session(session_id: str):
    return handle(web_cv.reset_session, session_id)


@router.delete("/web-cv/sessions/{session_id}")
def web_cv_delete_session(session_id: str):
    return web_cv.delete_session(session_id)


@router.post("/web-cv/package-quality/analyze")
async def web_cv_package_quality(session_id: str = Form(...), file: UploadFile = File(...)):
    return await handle_async(web_cv.analyze_package_quality, session_id, await file.read(), file.filename, file.content_type)


@router.post("/web-cv/dispatch/scan")
async def web_cv_dispatch_scan(session_id: str = Form(...), context_id: str = Form("CTX-JKT-BAY-02"), file: UploadFile = File(...)):
    return await handle_async(web_cv.validate_dispatch, session_id, await file.read(), file.filename, file.content_type, context_id)


@router.post("/web-cv/dispatch/validate-decoded")
def web_cv_dispatch_validate_decoded(payload: dict = Body(...)):
    return handle(
        web_cv.validate_dispatch_decoded,
        payload.get("session_id"),
        payload.get("qr_payload") or payload.get("raw_value") or {},
        payload.get("context_id", "CTX-JKT-BAY-02"),
        payload.get("qr_meta") or {},
    )


@router.post("/web-cv/loading/snapshot")
async def web_cv_loading_snapshot(session_id: str = Form(...), vehicle_id: str = Form("VAN-021"), file: UploadFile = File(...)):
    return await handle_async(web_cv.analyze_loading_snapshot, session_id, await file.read(), file.filename, file.content_type, vehicle_id)


@router.post("/web-cv/hub/start")
async def web_cv_hub_start(session_id: str = Form(...), file: UploadFile = File(...)):
    return await handle_async(web_cv.start_hub_journey, session_id, await file.read(), file.filename, file.content_type)


@router.post("/web-cv/hub/frame")
async def web_cv_hub_frame(session_id: str = Form(...), file: UploadFile = File(...)):
    return await handle_async(web_cv.observe_hub_journey, session_id, await file.read(), file.filename, file.content_type)


@router.post("/web-cv/hub/stop")
def web_cv_hub_stop(payload: dict = Body(...)):
    return handle(web_cv.stop_hub_journey, payload.get("session_id"))


@router.post("/web-cv/hub/reset")
def web_cv_hub_reset(payload: dict = Body(...)):
    return handle(web_cv.hub_reset, payload.get("session_id"))


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
