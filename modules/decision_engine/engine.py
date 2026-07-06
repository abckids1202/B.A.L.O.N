from __future__ import annotations

import hashlib
import json


def alert_id(alert_type: str, entity_id: str, title: str) -> str:
    key = f"{alert_type}:{entity_id}:{title}".encode()
    return hashlib.sha1(key).hexdigest()[:12].upper()


def sla_alert(shipment_id: str, probability: float, level: str, factors: list[str]) -> dict | None:
    if level not in {"High", "Critical"}:
        return None
    severity = "Critical" if level == "Critical" else "Warning"
    return {
        "alert_id": alert_id("SLA", shipment_id, level),
        "alert_type": "SLA_RISK",
        "entity_type": "Shipment",
        "entity_id": shipment_id,
        "severity": severity,
        "title": f"{level} SLA breach risk",
        "message": f"Shipment {shipment_id} has SLA breach probability {probability:.0%}.",
        "recommendation": "Review route optimization and hub conditions.",
        "evidence": {"probability": probability, "risk_level": level, "factors": factors},
    }


def hub_alert(analysis: dict) -> dict | None:
    if analysis["risk_level"] not in {"High", "Critical"}:
        return None
    return {
        "alert_id": alert_id("HUB", analysis["hub_id"], analysis["risk_level"]),
        "alert_type": "HUB_CONGESTION",
        "entity_type": "Hub",
        "entity_id": analysis["hub_id"],
        "severity": "Critical" if analysis["risk_level"] == "Critical" else "Warning",
        "title": f"{analysis['risk_level']} hub congestion",
        "message": f"{analysis['hub_id']} congestion score is {analysis['congestion_score']}.",
        "recommendation": f"Inspect likely bottleneck: {analysis['likely_bottleneck']}.",
        "evidence": analysis,
    }


def route_alert(shipment_id: str, recommendation: dict, explanation: str) -> dict:
    return {
        "alert_id": alert_id("ROUTE", shipment_id, recommendation["candidate_name"]),
        "alert_type": "ROUTE_RECOMMENDATION",
        "entity_type": "Shipment",
        "entity_id": shipment_id,
        "severity": "Watch",
        "title": "Route recommendation updated",
        "message": explanation,
        "recommendation": f"Use {recommendation['candidate_name']}.",
        "evidence": recommendation["metrics"],
    }
