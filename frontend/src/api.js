const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json();
}

export const api = {
  base: API_BASE,
  health: () => request("/health"),
  shipments: () => request("/api/shipments"),
  vehicles: () => request("/api/vehicles"),
  hubs: () => request("/api/hubs"),
  risk: (shipmentId) => request(`/api/risk/predict/${shipmentId}`, { method: "POST" }),
  riskHistory: (shipmentId) => request(`/api/risk/history/${shipmentId}`),
  packageJourneyView: (shipmentId) => request(`/api/packages/${shipmentId}/journey-view`),
  digitalTwin: (shipmentId) => request(`/api/packages/${shipmentId}/digital-twin`),
  interventions: (shipmentId) => request(`/api/interventions${shipmentId ? `?shipment_id=${shipmentId}` : ""}`),
  acceptIntervention: (interventionId) => request(`/api/interventions/${interventionId}/accept`, { method: "POST" }),
  rejectIntervention: (interventionId) => request(`/api/interventions/${interventionId}/reject`, { method: "POST" }),
  optimize: (payload) => request("/api/routes/optimize", { method: "POST", body: JSON.stringify(payload) }),
  hubRisk: () => request("/api/hubs/risk"),
  analyzeHub: (hubId) => request(`/api/hubs/analyze/${hubId}`, { method: "POST" }),
  fleet: () => request("/api/fleet/analyze", { method: "POST" }),
  maintenance: (vehicleId) => request(`/api/maintenance/analyze/${vehicleId}`, { method: "POST" }),
  simulationReset: () => request("/api/simulation/reset", { method: "POST" }),
  simulationNext: () => request("/api/simulation/next", { method: "POST" }),
  simulationPlay: () => request("/api/simulation/play", { method: "POST" }),
  simulationPause: () => request("/api/simulation/pause", { method: "POST" }),
  simulationState: () => request("/api/simulation/state"),
  analytics: () => request("/api/analytics/summary"),
  models: () => request("/api/models"),
  report: () => request("/api/reports/executive-summary"),
  alerts: () => request("/api/alerts"),
  providers: () => request("/api/providers/status"),
  snapshot: (shipmentId) => request(`/api/snapshots/${shipmentId}/current`),
  dataSources: () => request("/api/data-sources"),
  trainingData: () => request("/api/training-data/status"),
  operationalSignals: (entityId) => request(`/api/operational-signals${entityId ? `?entity_id=${entityId}` : ""}`),
  packageDamage: (shipmentId) => request(`/api/vision/package-damage?shipment_id=${shipmentId}`, { method: "POST" }),
  hubOccupancy: (hubId) => request(`/api/vision/hub-occupancy/${hubId}`, { method: "POST" }),
  hubOverflow: (hubId) => request(`/api/forecast/hub-overflow/${hubId}`, { method: "POST" }),
  loadingValidation: (shipmentId, observedVehicleId) => request(`/api/vision/loading-validation?shipment_id=${shipmentId}${observedVehicleId ? `&observed_vehicle_id=${observedVehicleId}` : ""}`, { method: "POST" }),
  visualDemoScenario: () => request("/api/vision/demo-scenario", { method: "POST" })
};
