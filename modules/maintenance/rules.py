from __future__ import annotations

from datetime import datetime


def maintenance_score(vehicle: dict, breakdowns: list[dict]) -> dict:
    km_since = max(vehicle["current_km"] - vehicle["last_service_km"], 0)
    try:
        days_since = (datetime.now() - datetime.fromisoformat(vehicle["last_service_date"])).days
    except Exception:
        days_since = 999
    penalties = []
    score = 100.0
    if km_since > 3500:
        penalty = min((km_since - 3500) / 80, 28)
        score -= penalty
        penalties.append(f"Km since service is {km_since:.0f}.")
    if days_since > 60:
        penalty = min((days_since - 60) / 3, 20)
        score -= penalty
        penalties.append(f"Days since service is {days_since}.")
    if breakdowns:
        score -= min(len(breakdowns) * 12, 24)
        penalties.append(f"{len(breakdowns)} breakdown history records found.")
    score = round(max(score, 0), 1)
    if score < 45:
        risk = "Service Recommended"
        days = 3
    elif score < 65:
        risk = "Check-Up Soon"
        days = 12
    elif score < 80:
        risk = "Needs Attention"
        days = 30
    else:
        risk = "Normal"
        days = 60
    return {"health_score": score, "risk_level": risk, "recommended_checkup_days": days, "factors": penalties or ["No major maintenance rule triggered."], "source": "Rule Fallback"}
