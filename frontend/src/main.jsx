import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  Brain,
  ClipboardList,
  Cloud,
  Map,
  Network,
  Play,
  RefreshCcw,
  Route,
  Server,
  Truck
} from "lucide-react";
import { api } from "./api";
import "./styles.css";

const nav = [
  ["Command Center", Activity],
  ["Delivery Risk", Brain],
  ["Route Optimizer", Route],
  ["Network Resilience", Network],
  ["Live Simulation", Play],
  ["Analytics", BarChart3],
  ["Data & Models", Server],
  ["Reports", ClipboardList]
];

function useAsync(loader, deps = []) {
  const [state, setState] = useState({ loading: true, error: "", data: null });
  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: "" }));
    loader()
      .then((data) => active && setState({ loading: false, error: "", data }))
      .catch((error) => active && setState({ loading: false, error: error.message, data: null }));
    return () => {
      active = false;
    };
  }, deps);
  return state;
}

function Header({ title, description }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <span className="badge synthetic">Synthetic demo environment</span>
    </header>
  );
}

function Card({ label, value, detail, tone = "blue" }) {
  return (
    <section className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </section>
  );
}

function Panel({ title, icon: Icon = Boxes, children }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <Icon size={18} />
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Button({ children, onClick, busy = false, secondary = false }) {
  return (
    <button className={secondary ? "button secondary" : "button"} onClick={onClick} disabled={busy}>
      {busy ? "Working..." : children}
    </button>
  );
}

function JsonBlock({ value }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}

function Status({ loading, error, children }) {
  if (loading) return <div className="state">Loading operational data...</div>;
  if (error) return <div className="error">Backend request failed: {error}</div>;
  return children;
}

function CommandCenter() {
  const summary = useAsync(api.analytics, []);
  return (
    <>
      <Header title="Command Center" description="Monitor delivery risk, hub conditions, carbon impact, and live alerts." />
      <Status {...summary}>
        {summary.data && (
          <>
            <div className="metrics-grid">
              <Card label="Active shipments" value={summary.data.active_shipments} />
              <Card label="Delayed risk" value={summary.data.predicted_delayed_shipments} tone="orange" />
              <Card label="Critical hubs" value={summary.data.critical_hub_count} tone="red" />
              <Card label="CO2 today" value={`${summary.data.daily_carbon_estimate_kg} kg`} tone="green" />
              <Card label="Fleet utilization" value={`${summary.data.fleet_utilization.fleet_utilization_score}%`} />
            </div>
            <div className="two-col">
              <Panel title="SLA Risk Distribution" icon={BarChart3}>
                <div className="bar-list">
                  {Object.entries(summary.data.risk_distribution).map(([label, value]) => (
                    <div key={label} className="bar-row">
                      <span>{label}</span>
                      <div><i style={{ width: `${Math.max(value * 20, 3)}%` }} /></div>
                      <b>{value}</b>
                    </div>
                  ))}
                </div>
              </Panel>
              <Panel title="Active Alerts" icon={AlertTriangle}>
                {summary.data.alerts.length === 0 ? <p className="muted">No active alerts yet. Run risk prediction or simulation.</p> :
                  summary.data.alerts.map((alert) => (
                    <article className="alert-card" key={alert.alert_id}>
                      <b>{alert.severity}: {alert.title}</b>
                      <p>{alert.message}</p>
                    </article>
                  ))
                }
              </Panel>
            </div>
          </>
        )}
      </Status>
    </>
  );
}

function DeliveryRisk({ shipments }) {
  const [shipmentId, setShipmentId] = useState("SHP-1028");
  const [risk, setRisk] = useState(null);
  const [history, setHistory] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try {
      const result = await api.risk(shipmentId);
      setRisk(result);
      setHistory(await api.riskHistory(shipmentId));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header title="Delivery Risk AI" description="Predict delay and SLA breach risk from shipment, traffic, weather, GPS, hub, and loading signals." />
      <Panel title="Shipment Risk Control" icon={Brain}>
        <div className="control-row">
          <select value={shipmentId} onChange={(event) => setShipmentId(event.target.value)}>
            {shipments.map((shipment) => <option key={shipment.shipment_id}>{shipment.shipment_id}</option>)}
          </select>
          <Button onClick={run} busy={busy}>Run Risk Prediction</Button>
        </div>
      </Panel>
      {risk && (
        <div className="metrics-grid">
          <Card label="Predicted delay" value={`${risk.predicted_delay_minutes} min`} />
          <Card label="SLA probability" value={`${Math.round(risk.sla_probability * 100)}%`} tone={risk.risk_level === "Critical" ? "red" : "orange"} />
          <Card label="Risk level" value={risk.risk_level} />
          <Card label="Model source" value={risk.model_source} />
        </div>
      )}
      {risk && <Panel title="Main Factors" icon={AlertTriangle}>{risk.main_factors.map((f) => <p key={f}>{f}</p>)}</Panel>}
      {history && <Panel title="Prediction History" icon={ClipboardList}><JsonBlock value={history} /></Panel>}
    </>
  );
}

function RouteOptimizer({ shipments, vehicles }) {
  const [shipmentId, setShipmentId] = useState("SHP-1028");
  const [vehicleId, setVehicleId] = useState("VAN-021");
  const [preset, setPreset] = useState("balanced_ai");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try {
      setResult(await api.optimize({ shipment_id: shipmentId, vehicle_id: vehicleId, preset }));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Header title="Green Route Optimizer" description="Compare route candidates across time, fuel, carbon, SLA risk, and decision-policy weights." />
      <Panel title="Optimization Inputs" icon={Map}>
        <div className="control-grid">
          <select value={shipmentId} onChange={(e) => setShipmentId(e.target.value)}>{shipments.map((s) => <option key={s.shipment_id}>{s.shipment_id}</option>)}</select>
          <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>{vehicles.map((v) => <option key={v.vehicle_id}>{v.vehicle_id}</option>)}</select>
          <select value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="balanced_ai">Balanced AI</option>
            <option value="fastest">Fastest</option>
            <option value="greenest">Greenest</option>
            <option value="sla_priority">SLA Priority</option>
          </select>
          <Button onClick={run} busy={busy}>Optimize Routes</Button>
        </div>
      </Panel>
      {result && (
        <>
          <Panel title="Recommendation" icon={Route}><p>{result.explanation}</p></Panel>
          <Panel title="Candidate Comparison" icon={BarChart3}>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Candidate</th><th>Distance</th><th>Time</th><th>Fuel</th><th>CO2</th><th>SLA Risk</th><th>Score</th></tr></thead>
                <tbody>{result.candidates.map((c) => (
                  <tr key={c.candidate_name}>
                    <td>{c.candidate_name}</td>
                    <td>{c.metrics.distance_km} km</td>
                    <td>{c.metrics.estimated_time_min} min</td>
                    <td>{c.metrics.fuel_liter} L</td>
                    <td>{c.metrics.co2_kg} kg</td>
                    <td>{Math.round(c.metrics.sla_risk * 100)}%</td>
                    <td>{c.metrics.objective_score}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </>
  );
}

function NetworkResilience({ hubs, vehicles }) {
  const [hubId, setHubId] = useState("HUB-BKS");
  const [vehicleId, setVehicleId] = useState("VAN-021");
  const [hub, setHub] = useState(null);
  const [fleet, setFleet] = useState(null);
  const [maintenance, setMaintenance] = useState(null);
  async function analyze() {
    setHub(await api.analyzeHub(hubId));
    setFleet(await api.fleet());
  }
  async function checkVehicle() {
    setMaintenance(await api.maintenance(vehicleId));
  }
  return (
    <>
      <Header title="Network Resilience" description="Detect hub bottlenecks, queue pressure, fleet utilization, and preventive check-up signals." />
      <Panel title="Hub Analysis" icon={Network}>
        <div className="control-row">
          <select value={hubId} onChange={(e) => setHubId(e.target.value)}>{hubs.map((h) => <option key={h.hub_id}>{h.hub_id}</option>)}</select>
          <Button onClick={analyze}>Analyze Hub & Fleet</Button>
        </div>
      </Panel>
      {hub && <div className="metrics-grid"><Card label="Congestion score" value={hub.congestion_score} /><Card label="Risk level" value={hub.risk_level} /><Card label="Queue growth" value={hub.queue_growth} /><Card label="Likely bottleneck" value={hub.likely_bottleneck} /></div>}
      {fleet && <Panel title="Fleet Utilization" icon={Truck}><JsonBlock value={fleet} /></Panel>}
      <Panel title="Maintenance Check-Up" icon={Truck}>
        <div className="control-row">
          <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>{vehicles.map((v) => <option key={v.vehicle_id}>{v.vehicle_id}</option>)}</select>
          <Button onClick={checkVehicle} secondary>Analyze Vehicle</Button>
        </div>
        {maintenance && <JsonBlock value={maintenance} />}
      </Panel>
    </>
  );
}

function LiveSimulation() {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.simulationState().then(setState).catch(() => null); }, []);
  async function action(fn) {
    setBusy(true);
    try { setState(await fn()); } finally { setBusy(false); }
  }
  return (
    <>
      <Header title="Live Simulation" description="Advance SHP-1028 traffic, weather, hub, and GPS events to trigger rescoring and recommendations." />
      <Panel title="Simulation Controls" icon={Play}>
        <div className="control-row">
          <Button onClick={() => action(api.simulationReset)} secondary busy={busy}>Reset</Button>
          <Button onClick={() => action(api.simulationNext)} busy={busy}>Next Event</Button>
        </div>
      </Panel>
      {state && <Panel title="Simulation State" icon={Cloud}><JsonBlock value={state} /></Panel>}
    </>
  );
}

function Analytics() {
  const summary = useAsync(api.analytics, []);
  return (
    <>
      <Header title="Analytics & Impact" description="Review computed route, fuel, carbon, SLA, and fleet impact assumptions." />
      <Status {...summary}>{summary.data && <JsonBlock value={summary.data} />}</Status>
    </>
  );
}

function DataModels() {
  const models = useAsync(api.models, []);
  return (
    <>
      <Header title="Data & Models" description="Inspect model registry metadata, synthetic dataset labels, metrics, and fallback states." />
      <Status {...models}>
        {models.data && <div className="table-wrap"><table><thead><tr><th>Name</th><th>Version</th><th>Type</th><th>Availability</th><th>Metrics</th></tr></thead><tbody>{models.data.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.version}</td><td>{m.model_type}</td><td>{m.availability}</td><td><code>{JSON.stringify(m.metrics)}</code></td></tr>)}</tbody></table></div>}
      </Status>
    </>
  );
}

function Reports() {
  const report = useAsync(api.report, []);
  const download = useMemo(() => report.data ? URL.createObjectURL(new Blob([JSON.stringify(report.data, null, 2)], { type: "application/json" })) : "", [report.data]);
  return (
    <>
      <Header title="Reports" description="Generate an executive summary and export the current synthetic demo state." />
      <Status {...report}>
        {report.data && <><a className="button" href={download} download="balon-executive-summary.json">Export JSON</a><JsonBlock value={report.data} /></>}
      </Status>
    </>
  );
}

function App() {
  const [page, setPage] = useState("Command Center");
  const bootstrap = useAsync(async () => {
    const [health, shipments, vehicles, hubs] = await Promise.all([api.health(), api.shipments(), api.vehicles(), api.hubs()]);
    return { health, shipments, vehicles, hubs };
  }, []);

  const shared = bootstrap.data || { shipments: [], vehicles: [], hubs: [] };
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">B</div>
          <div><strong>B.A.L.O.N</strong><span>Logistics AI</span></div>
        </div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button key={label} className={page === label ? "active" : ""} onClick={() => setPage(label)}>
              <Icon size={18} /> {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>API</span>
          <b>{api.base}</b>
        </div>
      </aside>
      <main>
        <Status {...bootstrap}>
          {page === "Command Center" && <CommandCenter />}
          {page === "Delivery Risk" && <DeliveryRisk shipments={shared.shipments} />}
          {page === "Route Optimizer" && <RouteOptimizer shipments={shared.shipments} vehicles={shared.vehicles} />}
          {page === "Network Resilience" && <NetworkResilience hubs={shared.hubs} vehicles={shared.vehicles} />}
          {page === "Live Simulation" && <LiveSimulation />}
          {page === "Analytics" && <Analytics />}
          {page === "Data & Models" && <DataModels />}
          {page === "Reports" && <Reports />}
        </Status>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
