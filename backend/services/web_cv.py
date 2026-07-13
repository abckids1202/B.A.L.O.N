from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

from backend.services import core
from cv_worker.detectors.package_yolo import detect_packages
from cv_worker.detectors.qr_reader import QRReader
from cv_worker.config import ROOT, config as cv_config
from cv_worker.model_registry import damage_model, package_model, registry
from cv_worker.tracking.marker_logic import DEFAULT_HUB_ZONES, DEFAULT_LOADING_CONFIG, HubJourneySession, LoadingInspectionState, make_yolo_candidate
from database import repositories as repo
from database.connection import initialize_database


MODULES = {"PACKAGE_QUALITY", "DISPATCH_VALIDATION", "LOADING_COMPLIANCE", "HUB_JOURNEY"}
SOURCE_MODES = {"LIVE_CAMERA", "UPLOAD", "DEMO_SAMPLE", "REPLAY", "LOCAL_WORKER"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


WEB_CV_ENABLED = _env_bool("CV_WEB_ENABLED", True)
MAX_UPLOAD_MB = float(os.getenv("CV_MAX_UPLOAD_MB", "6"))
MAX_IMAGE_DIMENSION = int(os.getenv("CV_MAX_IMAGE_DIMENSION", "1600"))
CONFIDENCE_THRESHOLD = float(os.getenv("CV_CONFIDENCE_THRESHOLD", "0.75"))
LOADING_MAX_PACKAGES = int(os.getenv("CV_LOADING_MAX_PACKAGES", "5"))
MAX_CONCURRENT_INFERENCE = max(1, int(os.getenv("CV_WEB_MAX_CONCURRENT_INFERENCE", "1")))
INFERENCE_TIMEOUT_SECONDS = float(os.getenv("CV_WEB_INFERENCE_TIMEOUT_SECONDS", "30"))
SESSION_TTL_SECONDS = int(float(os.getenv("CV_WEB_SESSION_TTL_MINUTES", "30")) * 60)

_inference_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INFERENCE)
_qr_reader: QRReader | None = None


@dataclass
class WebCvSession:
    session_id: str
    module: str
    processing_mode: str
    status: str = "READY"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + SESSION_TTL_SECONDS)
    latest_observation: dict[str, Any] | None = None
    latest_analysis: dict[str, Any] | None = None
    latest_decision: dict[str, Any] | None = None
    latest_impact: dict[str, Any] | None = None
    latest_event_id: str | None = None
    latest_evidence: dict[str, Any] | None = None
    error: str | None = None
    hub_state: HubJourneySession | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "module": self.module,
            "processing_mode": self.processing_mode,
            "status": self.status,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "expires_at": _iso(self.expires_at),
            "latest_observation": self.latest_observation,
            "latest_analysis": self.latest_analysis,
            "latest_decision": self.latest_decision,
            "latest_impact": self.latest_impact,
            "latest_event_id": self.latest_event_id,
            "latest_evidence": self.latest_evidence,
            "error": self.error,
        }


_sessions: dict[str, WebCvSession] = {}
_demo_seed_checked = False


def _iso(timestamp: float | None = None) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp or time.time(), tz=timezone.utc).astimezone(core.WIB).replace(microsecond=0).isoformat()


def _new_hub_state() -> HubJourneySession:
    return HubJourneySession(
        config=DEFAULT_HUB_ZONES,
        demo_baseline_seconds={
            "ZONE_1": float(os.getenv("CV_HUB_DEMO_ZONE_1_SECONDS", "10")),
            "ZONE_2": float(os.getenv("CV_HUB_DEMO_ZONE_2_SECONDS", "10")),
            "ZONE_3": float(os.getenv("CV_HUB_DEMO_ZONE_3_SECONDS", "4")),
        },
        real_baseline_hours={
            "ZONE_1": float(os.getenv("CV_HUB_REAL_ZONE_1_HOURS", "72.48")),
            "ZONE_2": float(os.getenv("CV_HUB_REAL_ZONE_2_HOURS", "72.00")),
            "ZONE_3": float(os.getenv("CV_HUB_REAL_ZONE_3_HOURS", "3.50")),
        },
    )


def _expire_sessions() -> None:
    now = time.time()
    for sid in [sid for sid, state in _sessions.items() if state.expires_at < now]:
        del _sessions[sid]


def _get_session(session_id: str) -> WebCvSession:
    _expire_sessions()
    state = _sessions.get(session_id)
    if not state:
        raise ValueError(f"Unknown or expired Web CV session {session_id}")
    state.updated_at = time.time()
    return state


def _ensure_demo_seeded() -> None:
    global _demo_seed_checked
    if _demo_seed_checked:
        return
    initialize_database()
    try:
        row = repo.row("SELECT name FROM sqlite_master WHERE type='table' AND name='cv_demo_packages'")
        package = repo.row("SELECT shipment_id FROM cv_demo_packages WHERE shipment_id='SHP-LOAD-001'") if row else None
        context = repo.row("SELECT loading_context_id FROM cv_demo_loading_contexts WHERE loading_context_id='CTX-JKT-BAY-01'") if row else None
        if not package or not context:
            from scripts import seed_cv_demo_data

            seed_cv_demo_data.ensure_tables()
            seed_cv_demo_data.upsert_hubs()
            seed_cv_demo_data.upsert_vehicles_and_drivers()
            seed_cv_demo_data.upsert_shipments_and_packages()
            seed_cv_demo_data.upsert_routes()
            seed_cv_demo_data.upsert_contexts()
    finally:
        _demo_seed_checked = True


def health() -> dict[str, Any]:
    _expire_sessions()
    package_path = Path(cv_config.package_model_path)
    damage_path = Path(cv_config.damage_model_path)
    package_resolved = package_path if package_path.is_absolute() else ROOT / package_path
    damage_resolved = damage_path if damage_path.is_absolute() else ROOT / damage_path
    package_status = "AVAILABLE" if package_resolved.exists() else "FILE_NOT_FOUND"
    damage_status = "AVAILABLE" if damage_resolved.exists() else "FILE_NOT_FOUND"
    return {
        "status": "ONLINE" if WEB_CV_ENABLED else "DISABLED",
        "web_cv_enabled": WEB_CV_ENABLED,
        "models_ready": package_status == "AVAILABLE" and damage_status == "AVAILABLE",
        "package_model": package_status,
        "damage_model": damage_status,
        "active_sessions": len(_sessions),
        "inference_capacity": {"maximum": MAX_CONCURRENT_INFERENCE, "available": 1 if not _inference_semaphore.locked() else 0},
    }


def model_status() -> dict[str, Any]:
    assets = registry()
    return {
        "package_model": {
            "status": assets.get("package", {}).get("status"),
            "provider": assets.get("package", {}).get("provider"),
            "classes": assets.get("package", {}).get("classes"),
            "normalized_class": "PACKAGE",
            "error": assets.get("package", {}).get("error"),
        },
        "damage_model": {
            "status": assets.get("damage", {}).get("status"),
            "provider": assets.get("damage", {}).get("provider"),
            "labels": assets.get("damage", {}).get("classes"),
            "error": assets.get("damage", {}).get("error"),
        },
    }


def create_session(module: str, processing_mode: str = "LIVE_CAMERA") -> dict[str, Any]:
    module = module.upper()
    processing_mode = processing_mode.upper().replace("WEB_LIVE", "LIVE_CAMERA")
    if module not in MODULES:
        raise ValueError(f"Unsupported Web CV module {module}")
    if processing_mode not in SOURCE_MODES:
        raise ValueError(f"Unsupported processing mode {processing_mode}")
    sid = "WCV-" + uuid4().hex[:12].upper()
    state = WebCvSession(session_id=sid, module=module, processing_mode=processing_mode)
    if module == "HUB_JOURNEY":
        state.hub_state = _new_hub_state()
    _sessions[sid] = state
    return state.as_dict()


def get_session(session_id: str) -> dict[str, Any]:
    return _get_session(session_id).as_dict()


def reset_session(session_id: str) -> dict[str, Any]:
    state = _get_session(session_id)
    module = state.module
    mode = state.processing_mode
    fresh = WebCvSession(session_id=session_id, module=module, processing_mode=mode)
    state.__dict__.update(fresh.__dict__)
    if module == "HUB_JOURNEY":
        state.hub_state = _new_hub_state()
    return state.as_dict()


def delete_session(session_id: str) -> dict[str, Any]:
    existed = session_id in _sessions
    _sessions.pop(session_id, None)
    return {"deleted": existed, "session_id": session_id}


def _decode_image(content: bytes, filename: str | None, content_type: str | None) -> tuple[np.ndarray, dict[str, Any]]:
    if not content:
        raise ValueError("INVALID_IMAGE: empty upload")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"IMAGE_TOO_LARGE: maximum upload is {MAX_UPLOAD_MB:g} MB")
    guessed = content_type or mimetypes.guess_type(filename or "")[0] or ""
    if guessed not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError("INVALID_IMAGE: upload must be JPEG, PNG, or WEBP")
    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise ValueError(f"MODEL_NOT_READY: OpenCV is not available ({exc})")
    array = np.frombuffer(content, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None or not frame.size:
        raise ValueError("INVALID_IMAGE: could not decode image")
    height, width = frame.shape[:2]
    scale = min(1.0, MAX_IMAGE_DIMENSION / max(width, height, 1))
    if scale < 1:
        frame = cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        height, width = frame.shape[:2]
    digest = hashlib.sha1(content).hexdigest()
    return frame, {"filename": filename or "snapshot.jpg", "content_type": guessed, "image_width": width, "image_height": height, "sha1": digest[:16]}


async def _run_inference(fn, *args, **kwargs):
    try:
        await asyncio.wait_for(_inference_semaphore.acquire(), timeout=0.25)
    except asyncio.TimeoutError as exc:
        raise RuntimeError("CV_INFERENCE_BUSY") from exc
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn, *args, **kwargs), timeout=INFERENCE_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise RuntimeError("INFERENCE_TIMEOUT") from exc
    finally:
        _inference_semaphore.release()


def _detect(frame: np.ndarray) -> dict[str, Any]:
    model = package_model()
    if model is None:
        raise ValueError("MODEL_NOT_READY: package model is not loaded")
    return detect_packages(model, frame, CONFIDENCE_THRESHOLD)


def _normalize_detection(item: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    x1, y1, x2, y2 = [float(v) for v in item.get("bbox", [0, 0, 0, 0])]
    return {
        **item,
        "bbox": {
            "x1": round(max(0.0, min(1.0, x1 / max(width, 1))), 4),
            "y1": round(max(0.0, min(1.0, y1 / max(height, 1))), 4),
            "x2": round(max(0.0, min(1.0, x2 / max(width, 1))), 4),
            "y2": round(max(0.0, min(1.0, y2 / max(height, 1))), 4),
        },
    }


def _best_package(detections: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max([item for item in detections if item.get("normalized_class") == "PACKAGE"], key=lambda item: float(item.get("confidence", 0)), default=None)


def _event(event_type: str, module: str, payload: dict[str, Any], **extra) -> dict[str, Any]:
    event = {
        "event_id": "CVE-WEB-" + hashlib.sha1(repo.jdump({"event_type": event_type, "payload": payload, "time": core.now_iso()}).encode("utf-8")).hexdigest()[:16].upper(),
        "event_type": event_type,
        "module": module,
        "source": "WEB_ASSESSOR",
        "camera_id": "WEB-BROWSER",
        "observed_at": core.now_iso(),
        "confidence": float(extra.pop("confidence", payload.get("confidence", 0.8) or 0.8)),
        "severity": extra.pop("severity", "INFO"),
        "payload": payload,
        **extra,
    }
    return core.ingest_cv_event(event)


def _envelope(state: WebCvSession, observation: dict, analysis: dict, decision: dict, impact: dict, evidence: dict, event: dict | None) -> dict:
    state.latest_observation = observation
    state.latest_analysis = analysis
    state.latest_decision = decision
    state.latest_impact = impact
    state.latest_evidence = evidence
    state.latest_event_id = event.get("event_id") if event else None
    state.status = "DECISION_RECEIVED" if event else "RESULT_READY"
    state.updated_at = time.time()
    state.error = None
    return {"session": state.as_dict(), "observation": observation, "analysis": analysis, "decision": decision, "impact": impact, "evidence": evidence, "event": event}


async def analyze_package_quality(session_id: str, content: bytes, filename: str | None, content_type: str | None) -> dict:
    initialize_database()
    state = _get_session(session_id)
    state.status = "PROCESSING"
    frame, evidence = _decode_image(content, filename, content_type)
    height, width = frame.shape[:2]
    detection_result = await _run_inference(_detect, frame)
    detections = detection_result.get("detections", [])
    best = _best_package(detections)
    if not best:
        raise ValueError("NO_PACKAGE_DETECTED: place one package clearly in view and retry")
    x1, y1, x2, y2 = [int(v) for v in best["bbox"]]
    crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
    classifier = damage_model()
    if classifier is None:
        raise ValueError("MODEL_NOT_READY: damage model is not loaded")
    damage = await _run_inference(classifier.predict, crop if crop.size else frame)
    damaged = damage["label"] == "DAMAGED"
    payload = {
        "detected_package": _normalize_detection(best, width, height),
        "damage_status": damage["label"],
        "damage_confidence": round(float(damage["confidence"]), 4),
        "inspection_required": damaged,
        "condition_score": round((1.0 - float(damage["confidence"]) if damaged else float(damage["confidence"])) * 100, 1),
        "processing_mode": state.processing_mode,
    }
    event = _event("PACKAGE_DAMAGE_DETECTED", "PACKAGE_QUALITY", payload, shipment_id="SHP-DMG-001", package_id="PKG-DMG-001", hub_id="HUB-JKT", severity="HIGH" if damaged else "INFO", confidence=damage["confidence"])
    observation = {"packages": [_normalize_detection(item, width, height) for item in detections], "selected_package": payload["detected_package"]}
    analysis = {"package_detection_ms": detection_result.get("processing_time_ms"), "damage": damage, "model": "YOLO_PACKAGE_PLUS_DAMAGE_CLASSIFIER"}
    decision = {"status": "INSPECTION_REQUIRED" if damaged else "CLEAR", "recommendation": "Hold package for inspection" if damaged else "Continue to dispatch validation"}
    impact = {"digital_twin": "quality_context_updated", "next_step": "Dispatch Validation", "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, analysis, decision, impact, evidence, event)


def _scan_qr(frame: np.ndarray) -> dict | None:
    global _qr_reader
    _qr_reader = _qr_reader or QRReader()
    return _qr_reader.scan(frame)


def _demo_package(shipment_id: str) -> dict:
    _ensure_demo_seeded()
    row = repo.row("SELECT * FROM cv_demo_packages WHERE shipment_id=?", (shipment_id,))
    if row:
        return dict(row)
    return core.package_qr_identity_context(shipment_id)


def _loading_context(context_id: str) -> dict:
    _ensure_demo_seeded()
    row = repo.row("SELECT * FROM cv_demo_loading_contexts WHERE loading_context_id=?", (context_id,))
    if not row:
        raise ValueError(f"Unknown loading context {context_id}")
    return dict(row)


async def validate_dispatch(session_id: str, content: bytes, filename: str | None, content_type: str | None, context_id: str = "CTX-JKT-BAY-02") -> dict:
    initialize_database()
    state = _get_session(session_id)
    state.status = "SCANNING"
    frame, evidence = _decode_image(content, filename, content_type)
    qr = await _run_inference(_scan_qr, frame)
    if not qr:
        raise ValueError("QR_UNREADABLE: hold SHP-LOAD-001 steady and retry")
    payload = qr.get("payload") or {}
    shipment_id = str(payload.get("shipment_id") or "")
    if not shipment_id:
        raise ValueError("MALFORMED_QR: QR payload must contain shipment_id")
    package = _demo_package(shipment_id)
    context = _loading_context(context_id)
    planned_vehicle = package.get("planned_vehicle_id") or package.get("planned_vehicle")
    mismatch = planned_vehicle != context["current_vehicle_id"]
    status = "WRONG_VEHICLE" if mismatch else "VALID"
    event_payload = {
        "qr": qr,
        "shipment_id": shipment_id,
        "package_id": payload.get("package_id") or package.get("package_id"),
        "planned_vehicle_id": planned_vehicle,
        "active_context": context,
        "validation_result": status,
        "dispatch_state": "BLOCKED" if mismatch else "READY",
    }
    event = _event("PACKAGE_LOADING_MISMATCH" if mismatch else "PACKAGE_LOADING_VALIDATED", "DISPATCH_VALIDATION", event_payload, shipment_id=shipment_id, package_id=event_payload["package_id"], vehicle_id=context["current_vehicle_id"], hub_id=context["hub_id"], severity="CRITICAL" if mismatch else "INFO", confidence=0.94 if mismatch else 0.88)
    observation = {"qr": qr, "shipment_id": shipment_id, "package_id": event_payload["package_id"]}
    analysis = {"planned_assignment": package, "active_context": context, "comparison": status}
    decision = {"status": status, "dispatch": "BLOCKED" if mismatch else "READY", "recommendation": "Move package to VAN-021" if mismatch else "Release package to loading"}
    impact = {"vehicle_assignment": "mismatch_detected" if mismatch else "validated", "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, analysis, decision, impact, evidence, event)


async def analyze_loading_snapshot(session_id: str, content: bytes, filename: str | None, content_type: str | None, vehicle_id: str = "VAN-021") -> dict:
    initialize_database()
    state = _get_session(session_id)
    state.status = "PROCESSING"
    frame, evidence = _decode_image(content, filename, content_type)
    height, width = frame.shape[:2]
    detection_result = await _run_inference(_detect, frame)
    loading = LoadingInspectionState(limit=LOADING_MAX_PACKAGES, config=DEFAULT_LOADING_CONFIG)
    summary = loading.capture(detection_result.get("detections", []), width, height, CONFIDENCE_THRESHOLD)
    event = _event("PROTOTYPE_LOAD_LIMIT_EXCEEDED" if summary["excess_count"] else "LOADING_COMPLIANCE_VALIDATED", "LOADING_COMPLIANCE", summary, vehicle_id=vehicle_id, hub_id="HUB-JKT", severity="CRITICAL" if summary["excess_count"] else "INFO", confidence=0.9)
    observation = {"packages": [_normalize_detection(item, width, height) for item in detection_result.get("detections", [])], "roi": summary["roi"]}
    analysis = {**summary, "valid_detections": [_normalize_detection(item, width, height) for item in summary["valid_detections"]], "package_detection_ms": detection_result.get("processing_time_ms")}
    decision = {"status": summary["capacity_status"], "dispatch": summary["dispatch_state"], "recommendation": summary["recommendation"]}
    impact = {"vehicle_digital_twin": "load_state_updated", "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, analysis, decision, impact, evidence, event)


async def _hub_candidate_from_image(content: bytes, filename: str | None, content_type: str | None) -> tuple[dict | None, dict, int, int, list[dict]]:
    frame, evidence = _decode_image(content, filename, content_type)
    height, width = frame.shape[:2]
    detection_result = await _run_inference(_detect, frame)
    best = _best_package(detection_result.get("detections", []))
    candidate = make_yolo_candidate(best, stable_frames=3) if best else None
    return candidate, evidence, width, height, detection_result.get("detections", [])


async def start_hub_journey(session_id: str, content: bytes, filename: str | None, content_type: str | None) -> dict:
    state = _get_session(session_id)
    state.hub_state = state.hub_state or _new_hub_state()
    candidate, evidence, width, height, detections = await _hub_candidate_from_image(content, filename, content_type)
    summary = state.hub_state.start(candidate, width, height, "YOLO_SINGLE_PACKAGE")
    state.status = "RUNNING" if not summary.get("last_error") else "FAILED"
    state.error = summary.get("last_error")
    event = _event("HUB_JOURNEY_STARTED", "HUB_VISION", summary, shipment_id="SHP-HUB-001", hub_id="HUB-JKT", severity="INFO", confidence=float((candidate or {}).get("confidence", 0.8)))
    observation = {"candidate": summary.get("candidate"), "packages": [_normalize_detection(item, width, height) for item in detections]}
    decision = {"status": summary["status"], "recommendation": summary.get("instruction")}
    impact = {"hub_twin": "journey_timer_started", "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, summary, decision, impact, evidence, event)


async def observe_hub_journey(session_id: str, content: bytes, filename: str | None, content_type: str | None) -> dict:
    state = _get_session(session_id)
    state.hub_state = state.hub_state or _new_hub_state()
    candidate, evidence, width, height, detections = await _hub_candidate_from_image(content, filename, content_type)
    summary = state.hub_state.update(candidate, width, height, "YOLO_SINGLE_PACKAGE")
    transition = summary.get("last_transition") or {}
    event_type = "HUB_PROJECTED_DWELL_UPDATED"
    if transition.get("to") == "ZONE_2":
        event_type = "HUB_PACKAGE_MOVED_TO_PROCESSING"
    elif transition.get("to") == "ZONE_3":
        event_type = "HUB_PACKAGE_MOVED_TO_DISPATCH"
    event = _event(event_type, "HUB_VISION", summary, shipment_id="SHP-HUB-001", hub_id="HUB-JKT", severity=summary.get("risk_level", "INFO"), confidence=float((candidate or {}).get("confidence", 0.82)))
    observation = {"candidate": summary.get("candidate"), "packages": [_normalize_detection(item, width, height) for item in detections]}
    decision = {"status": summary["status"], "risk_level": summary["risk_level"], "recommendation": "Continue journey" if summary["status"] == "RUNNING" else summary.get("instruction")}
    impact = {"projected_real_dwell_hours": summary["projected_real_dwell_hours"], "estimated_delay_hours": summary["estimated_delay_hours"], "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, summary, decision, impact, evidence, event)


def stop_hub_journey(session_id: str) -> dict:
    state = _get_session(session_id)
    state.hub_state = state.hub_state or _new_hub_state()
    summary = state.hub_state.stop("YOLO_SINGLE_PACKAGE")
    event = _event("HUB_JOURNEY_COMPLETED", "HUB_VISION", summary, shipment_id="SHP-HUB-001", hub_id="HUB-JKT", severity=summary.get("risk_level", "INFO"), confidence=0.9)
    observation = {"candidate": summary.get("candidate")}
    decision = {"status": "JOURNEY_COMPLETED", "risk_level": summary["risk_level"], "recommendation": "Use final dwell projection in hub planning"}
    impact = {"actual_total_seconds": summary.get("actual_total_seconds"), "projected_real_dwell_hours": summary["projected_real_dwell_hours"], "estimated_delay_hours": summary["estimated_delay_hours"], "event_type": event["observation"]["event_type"]}
    return _envelope(state, observation, summary, decision, impact, {}, event)


def hub_reset(session_id: str) -> dict:
    state = _get_session(session_id)
    state.hub_state = _new_hub_state()
    state.status = "READY"
    state.latest_observation = state.latest_analysis = state.latest_decision = state.latest_impact = state.latest_evidence = None
    state.latest_event_id = None
    state.error = None
    return state.as_dict()
