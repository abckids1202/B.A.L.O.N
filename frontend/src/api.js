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

async function upload(path, formData, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 45000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: formData,
      signal: controller.signal
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${response.status} ${response.statusText}: ${text}`);
    }
    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  base: API_BASE,
  health: () => request("/health"),
  shipments: () => request("/api/shipments"),
  shipmentsPaged: (params = {}) => request(`/api/shipments/paged?${new URLSearchParams(params)}`),
  vehicles: () => request("/api/vehicles"),
  vehiclesPaged: (params = {}) => request(`/api/vehicles/paged?${new URLSearchParams(params)}`),
  drivers: (params = {}) => request(`/api/drivers?${new URLSearchParams(params)}`),
  networkSummary: () => request("/api/network/summary"),
  clock: () => request("/api/clock"),
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
  visualDemoScenario: () => request("/api/vision/demo-scenario", { method: "POST" }),
  cvState: () => request("/api/cv/state"),
  cvEvents: (limit = 40) => request(`/api/cv/events?limit=${limit}`),
  cvReplay: (scenario = "ALL") => request(`/api/cv/demo-replay?scenario=${scenario}`, { method: "POST" }),
  cvIngest: (event) => request("/api/cv/events", { method: "POST", body: JSON.stringify(event) }),
  visualAssets: () => request("/api/visual-intelligence/assets"),
  visualSummary: () => request("/api/visual-intelligence/summary"),
  qrIdentity: (shipmentId) => request(`/api/visual-intelligence/qr-identity/${shipmentId}`),
  packageQuality: (shipmentId = "SHP-1028") => request(`/api/visual-intelligence/package-quality?shipment_id=${shipmentId}`, { method: "POST" }),
  dispatchValidation: (shipmentId = "SHP-1028", observedVehicleId = "VAN-044") => request(`/api/visual-intelligence/dispatch-validation?shipment_id=${shipmentId}&observed_vehicle_id=${observedVehicleId}`, { method: "POST" }),
  loadingCompliance: (vehicleId = "TRK-001", loadedPackages = 6, visualCapacity = 5) => request(`/api/visual-intelligence/loading-compliance?vehicle_id=${vehicleId}&loaded_packages=${loadedPackages}&visual_capacity=${visualCapacity}`, { method: "POST" }),
  hubVision: (hubId = "HUB-JKT", observedPackages) => request(`/api/visual-intelligence/hub-vision?hub_id=${hubId}${observedPackages ? `&observed_packages=${observedPackages}` : ""}`, { method: "POST" }),
  webCvHealth: () => request("/api/web-cv/health"),
  webCvModelStatus: () => request("/api/web-cv/models/status"),
  webCvCreateSession: (module, processingMode = "LIVE_CAMERA") => request("/api/web-cv/sessions", { method: "POST", body: JSON.stringify({ module, processing_mode: processingMode }) }),
  webCvResetSession: (sessionId) => request(`/api/web-cv/sessions/${sessionId}/reset`, { method: "POST" }),
  webCvDeleteSession: (sessionId) => request(`/api/web-cv/sessions/${sessionId}`, { method: "DELETE" }),
  webCvPackageQuality: (sessionId, file) => {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("file", file, file.name || "package-quality.jpg");
    return upload("/api/web-cv/package-quality/analyze", form);
  },
  webCvDispatchScan: (sessionId, file, contextId = "CTX-JKT-BAY-02") => {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("context_id", contextId);
    form.append("file", file, file.name || "dispatch-qr.jpg");
    return upload("/api/web-cv/dispatch/scan", form);
  },
  webCvDispatchValidateDecoded: (sessionId, qrPayload, contextId = "CTX-JKT-BAY-02", qrMeta = {}) => request("/api/web-cv/dispatch/validate-decoded", { method: "POST", body: JSON.stringify({ session_id: sessionId, qr_payload: qrPayload, context_id: contextId, qr_meta: qrMeta }) }),
  webCvLoadingSnapshot: (sessionId, file, vehicleId = "VAN-021") => {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("vehicle_id", vehicleId);
    form.append("file", file, file.name || "loading-snapshot.jpg");
    return upload("/api/web-cv/loading/snapshot", form);
  },
  webCvHubStart: (sessionId, file) => {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("file", file, file.name || "hub-start.jpg");
    return upload("/api/web-cv/hub/start", form);
  },
  webCvHubFrame: (sessionId, file) => {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("file", file, file.name || "hub-frame.jpg");
    return upload("/api/web-cv/hub/frame", form);
  },
  webCvHubStop: (sessionId) => request("/api/web-cv/hub/stop", { method: "POST", body: JSON.stringify({ session_id: sessionId }) }),
  webCvHubReset: (sessionId) => request("/api/web-cv/hub/reset", { method: "POST", body: JSON.stringify({ session_id: sessionId }) })
};
