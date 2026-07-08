import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Boxes,
  Brain,
  ClipboardList,
  Database,
  Gauge,
  Map,
  Network,
  PackageSearch,
  Play,
  RefreshCcw,
  Route,
  Server,
  Truck
} from "lucide-react";
import { api } from "./api";
import "./styles.css";

const nav = [
  ["Overview", Activity],
  ["Package Reports", PackageSearch],
  ["Analytics", BarChart3],
  ["Route Planning", Route],
  ["Fleet", Truck],
  ["Data & Models", Server]
];

const palette = ["#2563eb", "#0f9d8a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#84cc16", "#f97316"];

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

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function fmt(value, unit = "") {
  const number = safeNumber(value);
  const shown = Number.isInteger(number) ? number : number.toFixed(1);
  return `${shown}${unit}`;
}

function countBy(items, getter) {
  return items.reduce((acc, item) => {
    const key = getter(item) || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function toSeries(record, labelMap = {}) {
  return Object.entries(record || {}).map(([label, value]) => ({
    label: labelMap[label] || label,
    value: safeNumber(value)
  }));
}

function normalizeStatus(value) {
  return String(value || "unknown").replaceAll("_", " ").toLowerCase();
}

function riskTone(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("critical") || text.includes("high")) return "red";
  if (text.includes("medium") || text.includes("warning")) return "orange";
  return "green";
}

function shipmentStage(shipment) {
  const status = normalizeStatus(shipment.current_status || shipment.status);
  const priority = normalizeStatus(shipment.priority);
  if (status.includes("delivered")) return "Delivered";
  if (status.includes("hub")) return "Hub processing";
  if (priority.includes("same")) return "Inter-hub transport";
  if (status.includes("active") || status.includes("current")) return "Transport leg";
  return "Origin processing";
}

function Header({ title, description, action }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="header-actions">
        {action}
        <span className="badge synthetic">Synthetic journey intelligence</span>
      </div>
    </header>
  );
}

function Card({ label, value, detail, tone = "blue", icon: Icon }) {
  return (
    <section className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
      {Icon && <Icon className="metric-icon" size={18} />}
    </section>
  );
}

function Panel({ title, icon: Icon = Boxes, children, compact = false }) {
  return (
    <section className={compact ? "panel compact" : "panel"}>
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

function Status({ loading, error, children }) {
  if (loading) return <div className="state">Loading operational data...</div>;
  if (error) return <div className="error">Backend request failed: {error}</div>;
  return children;
}

function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>;
}

function BarChart({ title, data, unit = "", color = "#2563eb" }) {
  const max = Math.max(...data.map((d) => safeNumber(d.value)), 1);
  return (
    <div className="chart-card">
      {title && <h3>{title}</h3>}
      <div className="bar-chart" style={{ "--bar-color": color }}>
        {data.map((item) => (
          <div className="bar-column" key={item.label}>
            <div className="bar-track">
              <span style={{ height: `${Math.max((safeNumber(item.value) / max) * 100, item.value ? 8 : 2)}%` }} />
            </div>
            <b>{fmt(item.value, unit)}</b>
            <small>{item.label}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function HorizontalBars({ title, data, unit = "", color = "#2563eb" }) {
  const max = Math.max(...data.map((d) => safeNumber(d.value)), 1);
  return (
    <div className="chart-card">
      {title && <h3>{title}</h3>}
      <div className="hbars">
        {data.map((item) => (
          <div className="hbar-row" key={item.label}>
            <span>{item.label}</span>
            <div><i style={{ width: `${Math.max((safeNumber(item.value) / max) * 100, item.value ? 5 : 1)}%`, background: item.color || color }} /></div>
            <b>{fmt(item.value, unit)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function DonutChart({ title, data }) {
  const total = data.reduce((sum, item) => sum + safeNumber(item.value), 0) || 1;
  let offset = 25;
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="chart-card donut-card">
      {title && <h3>{title}</h3>}
      <div className="donut-layout">
        <svg viewBox="0 0 120 120" className="donut">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="18" />
          {data.map((item, index) => {
            const share = safeNumber(item.value) / total;
            const dash = share * circumference;
            const circle = (
              <circle
                key={item.label}
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={item.color || palette[index % palette.length]}
                strokeWidth="18"
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={offset}
              />
            );
            offset -= dash;
            return circle;
          })}
          <text x="60" y="56" textAnchor="middle">{Math.round(total)}</text>
          <text x="60" y="73" textAnchor="middle">total</text>
        </svg>
        <div className="legend">
          {data.map((item, index) => (
            <span key={item.label}><i style={{ background: item.color || palette[index % palette.length] }} />{item.label}: {item.value}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function GaugeCard({ label, value, max = 100, unit = "", tone = "blue" }) {
  const pct = Math.max(0, Math.min(100, (safeNumber(value) / max) * 100));
  return (
    <div className={`gauge-card ${tone}`}>
      <div className="gauge-ring" style={{ "--pct": `${pct}%` }}>
        <strong>{fmt(value, unit)}</strong>
      </div>
      <span>{label}</span>
    </div>
  );
}

function Sparkline({ points, color = "#2563eb" }) {
  const clean = points.map((p) => safeNumber(p));
  const max = Math.max(...clean, 1);
  const min = Math.min(...clean, 0);
  const spread = max - min || 1;
  const path = clean.map((value, index) => {
    const x = (index / Math.max(clean.length - 1, 1)) * 100;
    const y = 34 - ((value - min) / spread) * 28;
    return `${index ? "L" : "M"} ${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
  return (
    <svg className="sparkline" viewBox="0 0 100 40" preserveAspectRatio="none">
      <path d={path} fill="none" stroke={color} strokeWidth="3" />
    </svg>
  );
}

function Heatmap({ title, rows, columns, values }) {
  const max = Math.max(...Object.values(values).map((v) => safeNumber(v)), 1);
  return (
    <div className="chart-card">
      {title && <h3>{title}</h3>}
      <div className="heatmap">
        <span />
        {columns.map((column) => <b key={column}>{column}</b>)}
        {rows.flatMap((row) => [
          <strong key={`${row}-label`}>{row}</strong>,
          ...columns.map((column) => {
            const value = safeNumber(values[`${row}-${column}`]);
            return <i key={`${row}-${column}`} style={{ opacity: 0.16 + (value / max) * 0.84 }}>{value}</i>;
          })
        ])}
      </div>
    </div>
  );
}

function JourneyRail({ shipment, risk, snapshot, view }) {
  const viewStages = view?.journey_progress?.stages;
  const fallbackStage = shipmentStage(shipment);
  const stages = viewStages?.length ? viewStages : ["Origin", "Line haul", "Main hub", "Inter-hub", "Local hub", "Last mile", "Buyer"].map((label, index) => ({
    label,
    state: index === 0 ? "current" : "future"
  }));
  return (
    <div className="journey-rail">
      {stages.map((item) => (
        <div className={item.state === "complete" || item.state === "current" ? "rail-step active" : "rail-step"} key={item.key || item.label}>
          <i />
          <span>{item.label}</span>
        </div>
      ))}
      <div className="journey-context">
        <b>{shipment.shipment_id}</b>
        <span>{view?.current_state?.stage_label || fallbackStage}</span>
        {view?.latest_risk?.sla_probability != null && <small>{view.latest_risk.sla_level} SLA risk, {view.latest_risk.predicted_delay_minutes} min delay</small>}
        {!view && risk && <small>{risk.risk_level} SLA risk, {risk.predicted_delay_minutes} min delay</small>}
        {view?.latest_operational_snapshot && <small>{view.latest_operational_snapshot.weather_condition} / traffic {view.latest_operational_snapshot.traffic_index}</small>}
        {!view && snapshot && <small>{snapshot.weather?.condition || "weather"} / traffic {snapshot.traffic?.traffic_index ?? "n/a"}</small>}
      </div>
    </div>
  );
}

function RouteMap({ candidates = [] }) {
  const best = candidates[0];
  return (
    <div className="route-map">
      <svg viewBox="0 0 520 260" role="img" aria-label="Route candidate map">
        <path d="M52 198 C126 96 208 218 282 116 S407 52 468 148" className="route-path muted" />
        <path d="M52 198 C136 148 206 174 282 116 S395 95 468 148" className="route-path active" />
        <path d="M52 198 C104 226 220 96 312 132 S410 196 468 148" className="route-path alternate" />
        <circle cx="52" cy="198" r="11" className="pin origin" />
        <circle cx="282" cy="116" r="10" className="pin hub" />
        <circle cx="468" cy="148" r="12" className="pin destination" />
        <text x="34" y="226">Origin</text>
        <text x="260" y="98">Hub</text>
        <text x="424" y="132">Buyer zone</text>
      </svg>
      <div>
        <b>{best?.candidate_name || "Route candidates"}</b>
        <span>{best ? `${best.metrics.distance_km} km / ${best.metrics.estimated_time_min} min / ${best.metrics.co2_kg} kg CO2` : "Run an optimization to compare route shapes."}</span>
      </div>
    </div>
  );
}

function Timeline({ events }) {
  return (
    <div className="timeline">
      {events.map((event) => (
        <article key={event.event_id || `${event.title}-${event.time || event.event_at}`} className={event.tone || riskTone(event.severity)}>
          <time>{event.time || String(event.event_at || "").slice(11, 16) || "Now"}</time>
          <div>
            <b>{event.title}</b>
            <p>{event.description}</p>
          </div>
        </article>
      ))}
    </div>
  );
}

function makeJourneyEvents(shipment, risk, snapshot, simulationState) {
  const id = shipment?.shipment_id || "SHP-1028";
  const delay = risk?.predicted_delay_minutes ?? 14;
  const sla = risk ? Math.round(risk.sla_probability * 100) : 12;
  const hub = snapshot?.hub_event;
  const weather = snapshot?.weather;
  const processed = simulationState?.processed_event;
  return [
    { time: "08:00", title: `${id} created`, description: "Package journey opened from fulfillment origin.", tone: "green" },
    { time: "09:15", title: "Line-haul dispatched", description: `Vehicle ${shipment?.vehicle_id || "assigned"} started origin-to-hub transport.` },
    { time: "10:24", title: "Main hub arrival", description: `Package entered hub processing. Dwell target ${hub?.baseline_dwell_time_min || 41} min.` },
    { time: "11:49", title: "SLA risk updated", description: `${sla}% breach probability with ${delay} min predicted delay.`, tone: riskTone(risk?.risk_level) },
    { time: "12:10", title: "Operational snapshot rebuilt", description: `${weather?.condition || "Weather"} and traffic feeds refreshed for the active leg.` },
    processed ? { time: "Now", title: processed.event_type || "Demo event processed", description: `Source entity ${processed.entity_id || "demo provider"} changed the package journey.`, tone: "orange" } : null
  ].filter(Boolean);
}

function Overview({ shared }) {
  const summary = useAsync(api.analytics, []);
  const providers = useAsync(api.providers, []);
  const hubRisk = useAsync(api.hubRisk, []);
  const fleet = useAsync(api.fleet, []);
  const riskSeries = toSeries(summary.data?.risk_distribution, { Critical: "Critical", High: "High", Medium: "Medium", Low: "Low" });
  const prioritySeries = toSeries(countBy(shared.shipments, (s) => s.priority));
  const stageSeries = toSeries(countBy(shared.shipments, shipmentStage));
  const vehicleSeries = toSeries(countBy(shared.vehicles, (v) => v.engine_type || v.fuel_type || v.vehicle_type));
  const providerSeries = toSeries(countBy(providers.data || [], (p) => p.health));
  return (
    <>
      <Header title="Overview" description="A control tower for active packages, SLA exposure, hub pressure, fleet readiness, and carbon impact." />
      <Status {...summary}>
        {summary.data && (
          <>
            <div className="metrics-grid">
              <Card label="Active packages" value={summary.data.active_shipments} detail="current shipment journeys" icon={PackageSearch} />
              <Card label="High delay risk" value={summary.data.predicted_delayed_shipments} detail="latest risk predictions" tone="orange" icon={AlertTriangle} />
              <Card label="Critical hubs" value={summary.data.critical_hub_count} detail="network bottleneck watch" tone="red" icon={Network} />
              <Card label="CO2 today" value={`${summary.data.daily_carbon_estimate_kg} kg`} detail="estimated journey carbon" tone="green" icon={Gauge} />
              <Card label="Fleet utilization" value={`${summary.data.fleet_utilization.fleet_utilization_score}%`} detail="active vehicle ratio" icon={Truck} />
            </div>
            <div className="viz-grid">
              <BarChart title="SLA Risk Distribution" data={riskSeries} color="#dc2626" />
              <DonutChart title="Vehicles by Engine Type" data={vehicleSeries} />
              <HorizontalBars title="Package Journey Stages" data={stageSeries} color="#0f9d8a" />
              <DonutChart title="Provider Health" data={providerSeries.length ? providerSeries : [{ label: "healthy", value: 1 }]} />
              <BarChart title="Shipment Priority Mix" data={prioritySeries} color="#7c3aed" />
              <HorizontalBars title="Hub Congestion Score" data={(hubRisk.data || []).slice(0, 6).map((h) => ({ label: h.hub_id, value: h.congestion_score, color: riskTone(h.risk_level) === "red" ? "#dc2626" : "#f59e0b" }))} unit="%" color="#f59e0b" />
            </div>
            <div className="two-col">
              <Panel title="Active Package Journey" icon={PackageSearch}>
                <JourneyRail shipment={shared.shipments[0] || { shipment_id: "SHP-1028" }} />
              </Panel>
              <Panel title="Live Alert Feed" icon={AlertTriangle}>
                {summary.data.alerts?.length ? summary.data.alerts.map((alert) => (
                  <article className="alert-card" key={alert.alert_id}>
                    <b>{alert.severity}: {alert.title}</b>
                    <p>{alert.message}</p>
                  </article>
                )) : <EmptyState>No active alerts. Run a package risk check or demo event to generate interventions.</EmptyState>}
              </Panel>
            </div>
            {fleet.data && (
              <div className="gauge-grid">
                <GaugeCard label="Fleet utilization" value={fleet.data.fleet_utilization_score} unit="%" />
                <GaugeCard label="Active vehicle ratio" value={Math.round(fleet.data.active_vehicle_ratio * 100)} unit="%" tone="green" />
                <GaugeCard label="Idle vehicles" value={fleet.data.idle_vehicle_count} max={shared.vehicles.length || 1} tone="orange" />
                <GaugeCard label="High-use vehicles" value={fleet.data.high_use_vehicles?.length || 0} max={shared.vehicles.length || 1} tone="red" />
              </div>
            )}
          </>
        )}
      </Status>
    </>
  );
}

function PackageReports({ shared }) {
  const [shipmentId, setShipmentId] = useState(shared.shipments[0]?.shipment_id || "SHP-1028");
  const [view, setView] = useState(null);
  const [simulationState, setSimulationState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const shipment = view?.shipment || shared.shipments.find((s) => s.shipment_id === shipmentId) || shared.shipments[0] || {};
  const current = view?.latest_operational_snapshot || {};
  const risk = view?.latest_risk || {};

  async function loadView(id = shipmentId) {
    setBusy(true);
    setError("");
    try {
      const journey = await api.packageJourneyView(id);
      setView(journey);
      return journey;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    api.simulationState().then(setSimulationState).catch(() => null);
    loadView(shipmentId);
  }, [shipmentId]);

  async function simulation(fn) {
    setBusy(true);
    setError("");
    try {
      const next = await fn();
      setSimulationState(next);
      if (next.journey_view) {
        setView(next.journey_view);
      } else {
        await loadView(shipmentId);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const timeline = view?.timeline || makeJourneyEvents(shipment, null, null, simulationState);
  const factorData = (risk.factors || []).map((factor, index) => ({ label: factor.slice(0, 26), value: Math.max(100 - index * 18, 28) }));
  const slaHistory = Array.isArray(view?.risk_history?.sla) ? view.risk_history.sla : [];
  const historyData = slaHistory.slice(-8).reverse().map((item) => Math.round((item.sla_probability ?? 0) * 100));
  const carbonData = Object.entries(view?.carbon_summary?.stage_shares || { line_haul: 0.44, hub: 0.16, inter_hub: 0.25, last_mile: 0.15 }).map(([label, value]) => ({
    label: label.replaceAll("_", " "),
    value: Math.round(value * 100)
  }));
  const hubVisit = view?.current_hub_visit || {};

  return (
    <>
      <Header title="Package Reports" description="Follow a package from origin to buyer with one coherent journey view, risk state, event timeline, hub dwell, route decisions, and carbon context." />
      <Panel title="Package Selector and Demo Scenario" icon={PackageSearch}>
        <div className="control-row">
          <select value={shipmentId} onChange={(event) => setShipmentId(event.target.value)}>
            {shared.shipments.map((shipment) => <option key={shipment.shipment_id}>{shipment.shipment_id}</option>)}
          </select>
          <Button onClick={() => loadView()} busy={busy}>Refresh Package View</Button>
          <Button onClick={() => simulation(api.simulationReset)} busy={busy} secondary><RefreshCcw size={16} /> Reset Demo</Button>
          <Button onClick={() => simulation(api.simulationNext)} busy={busy}><Play size={16} /> Next Event</Button>
        </div>
        {busy && <p className="muted">Processing shipment event and rebuilding package intelligence...</p>}
        {error && <div className="error">Demo event processing failed: {error}</div>}
      </Panel>
      <JourneyRail shipment={shipment} view={view} />
      <div className="metrics-grid">
        <Card label="Current stage" value={view?.current_state?.stage_label || shipmentStage(shipment)} detail={view?.current_state?.location_id || shipment.current_status || "journey active"} />
        <Card label="Delay prediction" value={risk.predicted_delay_minutes != null ? `${risk.predicted_delay_minutes} min` : "n/a"} tone={riskTone(risk.sla_level)} />
        <Card label="SLA breach risk" value={risk.sla_probability != null ? `${Math.round(risk.sla_probability * 100)}%` : "n/a"} detail={risk.sla_level} tone={riskTone(risk.sla_level)} />
        <Card label="Traffic index" value={current.traffic_index ?? "n/a"} detail="latest provider snapshot" />
        <Card label="Hub dwell" value={current.hub_dwell_time_min != null ? `${current.hub_dwell_time_min} min` : "n/a"} detail={`${current.hub_dwell_excess_min ?? 0} min vs baseline`} />
      </div>
      <div className="two-col">
        <Panel title="Journey Timeline" icon={ClipboardList}>
          <Timeline events={timeline} />
        </Panel>
        <Panel title="Package Context" icon={Server}>
          <div className="gauge-grid tight">
            <GaugeCard label="Traffic" value={current.traffic_index ? current.traffic_index * 100 : 0} unit="%" tone="orange" />
            <GaugeCard label="Weather severity" value={current.weather_severity ? current.weather_severity * 100 : 0} unit="%" tone="blue" />
            <GaugeCard label="SLA risk" value={risk.sla_probability ? risk.sla_probability * 100 : 0} unit="%" tone={riskTone(risk.sla_level)} />
            <GaugeCard label="Delay" value={risk.predicted_delay_minutes || 0} max={120} unit="m" tone="red" />
          </div>
          {historyData.length > 1 && <Sparkline points={historyData} color="#dc2626" />}
        </Panel>
      </div>
      <div className="viz-grid">
        <HorizontalBars title="Risk Factor Strength" data={factorData.length ? factorData : [{ label: "No material factors yet", value: 5 }]} color="#dc2626" />
        <DonutChart title="Journey Carbon Allocation" data={carbonData} />
        <BarChart title="Hub Processing Minutes" data={[
          { label: "Unload", value: hubVisit.unloading_time_min || 0 },
          { label: "Sort", value: hubVisit.sorting_time_min || 0 },
          { label: "Dwell", value: hubVisit.dwell_time_min || 0 },
          { label: "Load", value: hubVisit.loading_time_min || 0 }
        ]} color="#0f9d8a" />
        <HorizontalBars title="Route Decisions" data={(view?.route_decisions || []).slice(0, 5).map((route) => ({ label: route.candidate_name, value: route.metrics?.objective_score || route.metrics?.co2_kg || 0 }))} color="#2563eb" />
        <Heatmap title="Journey Risk Heatmap" rows={["Origin", "Hub", "Route", "Last mile"]} columns={["Delay", "SLA", "Carbon"]} values={{ "Origin-Delay": 12, "Origin-SLA": 8, "Origin-Carbon": 22, "Hub-Delay": Math.round(current.hub_dwell_excess_min || 0), "Hub-SLA": Math.round((risk.sla_probability || 0) * 100), "Hub-Carbon": 16, "Route-Delay": Math.round((current.traffic_index || 0) * 100), "Route-SLA": Math.round((risk.sla_probability || 0) * 100), "Route-Carbon": 72, "Last mile-Delay": 31, "Last mile-SLA": 35, "Last mile-Carbon": 44 }} />
        <div className="chart-card narrative">
          <h3>Decision Activity</h3>
          {view?.latest_route_recommendation ? <p>{view.latest_route_recommendation.explanation}</p> : <p>No route intervention has been recorded yet.</p>}
          {(view?.alerts || []).slice(0, 3).map((alert) => <p key={alert.alert_id}><b>{alert.severity}</b>: {alert.title}</p>)}
        </div>
      </div>
    </>
  );
}

function Analytics() {
  const summary = useAsync(api.analytics, []);
  const hubRisk = useAsync(api.hubRisk, []);
  return (
    <>
      <Header title="Analytics" description="Journey-derived delay, carbon, hub dwell, fleet utilization, and AI intervention impact." />
      <Status {...summary}>
        {summary.data && (
          <>
            <div className="metrics-grid">
              <Card label="Distance avoided" value={`${summary.data.route_impact.distance_reduction_km ?? 0} km`} tone="green" />
              <Card label="Fuel avoided" value={`${summary.data.route_impact.fuel_reduction_liter ?? 0} L`} tone="green" />
              <Card label="CO2 avoided" value={`${summary.data.route_impact.co2_reduction_kg ?? 0} kg`} tone="green" />
              <Card label="SLA risk change" value={summary.data.route_impact.sla_risk_change ?? 0} tone="orange" />
              <Card label="Critical hubs" value={summary.data.critical_hub_count} tone="red" />
            </div>
            <div className="viz-grid">
              <BarChart title="Delay by Journey Stage" data={[{ label: "Origin", value: 9 }, { label: "Main hub", value: 42 }, { label: "Inter-hub", value: 31 }, { label: "Local hub", value: 18 }, { label: "Last mile", value: 24 }]} unit="m" color="#dc2626" />
              <DonutChart title="Carbon by Journey Stage" data={[{ label: "Line haul", value: 58 }, { label: "Hub", value: 18 }, { label: "Inter-hub", value: 34 }, { label: "Last mile", value: 41 }]} />
              <HorizontalBars title="Hub Dwell Pressure" data={(hubRisk.data || []).map((h) => ({ label: h.hub_id, value: h.congestion_score }))} unit="%" color="#f59e0b" />
              <BarChart title="AI Intervention Impact" data={[{ label: "Time", value: summary.data.route_impact.distance_reduction_km ?? 0 }, { label: "Fuel", value: summary.data.route_impact.fuel_reduction_liter ?? 0 }, { label: "CO2", value: summary.data.route_impact.co2_reduction_kg ?? 0 }, { label: "SLA", value: Math.abs(summary.data.route_impact.sla_risk_change ?? 0) }]} color="#2563eb" />
              <Heatmap title="Network Risk Matrix" rows={["HUB-JKT", "HUB-BKS", "HUB-TGR", "LM-ZONE"]} columns={["Queue", "Dwell", "SLA", "Carbon"]} values={{ "HUB-JKT-Queue": 71, "HUB-JKT-Dwell": 84, "HUB-JKT-SLA": 67, "HUB-JKT-Carbon": 25, "HUB-BKS-Queue": 48, "HUB-BKS-Dwell": 56, "HUB-BKS-SLA": 42, "HUB-BKS-Carbon": 18, "HUB-TGR-Queue": 25, "HUB-TGR-Dwell": 22, "HUB-TGR-SLA": 19, "HUB-TGR-Carbon": 15, "LM-ZONE-Queue": 36, "LM-ZONE-Dwell": 30, "LM-ZONE-SLA": 51, "LM-ZONE-Carbon": 69 }} />
              <div className="chart-card narrative">
                <h3>Executive Interpretation</h3>
                <p>{summary.data.assumptions}</p>
                <p>{summary.data.route_impact.baseline}</p>
                <Sparkline points={[12, 18, 16, 31, 27, 42, 35, 28, 24]} color="#0f9d8a" />
              </div>
            </div>
          </>
        )}
      </Status>
    </>
  );
}

function RoutePlanning({ shared }) {
  const [shipmentId, setShipmentId] = useState(shared.shipments[0]?.shipment_id || "SHP-1028");
  const [vehicleId, setVehicleId] = useState(shared.vehicles[0]?.vehicle_id || "VAN-021");
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
  const candidates = result?.candidates || [];
  return (
    <>
      <Header title="Route Planning" description="Map-first comparison of route choices across delivery time, fuel, carbon, SLA reliability, and objective score." />
      <Panel title="Route Evaluation Inputs" icon={Map}>
        <div className="control-grid">
          <select value={shipmentId} onChange={(e) => setShipmentId(e.target.value)}>{shared.shipments.map((s) => <option key={s.shipment_id}>{s.shipment_id}</option>)}</select>
          <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>{shared.vehicles.map((v) => <option key={v.vehicle_id}>{v.vehicle_id}</option>)}</select>
          <select value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="balanced_ai">Balanced AI</option>
            <option value="fastest">Fastest</option>
            <option value="greenest">Greenest</option>
            <option value="sla_priority">SLA Priority</option>
          </select>
          <Button onClick={run} busy={busy}>Evaluate Routes</Button>
        </div>
      </Panel>
      <div className="two-col map-first">
        <Panel title="Route Map" icon={Route}><RouteMap candidates={candidates} /></Panel>
        <Panel title="Recommendation" icon={Brain}>
          {result ? <><p>{result.explanation}</p><div className="recommendation-badge">{result.selected_candidate || candidates[0]?.candidate_name || "Recommended route"}</div></> : <EmptyState>Choose a shipment, vehicle, and objective, then evaluate routes.</EmptyState>}
        </Panel>
      </div>
      {result && (
        <div className="viz-grid">
          <BarChart title="Distance by Candidate" data={candidates.map((c) => ({ label: c.candidate_name, value: c.metrics.distance_km }))} unit="km" color="#2563eb" />
          <BarChart title="Time by Candidate" data={candidates.map((c) => ({ label: c.candidate_name, value: c.metrics.estimated_time_min }))} unit="m" color="#f59e0b" />
          <BarChart title="CO2 by Candidate" data={candidates.map((c) => ({ label: c.candidate_name, value: c.metrics.co2_kg }))} unit="kg" color="#0f9d8a" />
          <HorizontalBars title="SLA Risk by Candidate" data={candidates.map((c) => ({ label: c.candidate_name, value: Math.round(c.metrics.sla_risk * 100) }))} unit="%" color="#dc2626" />
        </div>
      )}
    </>
  );
}

function Fleet({ shared }) {
  const fleet = useAsync(api.fleet, []);
  const [vehicleId, setVehicleId] = useState(shared.vehicles[0]?.vehicle_id || "VAN-021");
  const [maintenance, setMaintenance] = useState(null);
  const [busy, setBusy] = useState(false);
  async function checkVehicle() {
    setBusy(true);
    try {
      setMaintenance(await api.maintenance(vehicleId));
    } finally {
      setBusy(false);
    }
  }
  const statusSeries = toSeries(countBy(shared.vehicles, (v) => v.status));
  const typeSeries = toSeries(countBy(shared.vehicles, (v) => v.vehicle_type || v.type));
  const utilization = shared.vehicles.map((vehicle, index) => ({
    label: vehicle.vehicle_id,
    value: safeNumber(vehicle.utilization_score ?? vehicle.daily_distance_km ?? (index + 2) * 11)
  }));
  return (
    <>
      <Header title="Fleet" description="Monitor vehicle utilization, active journey assignments, load balance, and preventive check-up recommendations." />
      <Status {...fleet}>
        {fleet.data && (
          <>
            <div className="metrics-grid">
              <Card label="Total vehicles" value={shared.vehicles.length} />
              <Card label="Active ratio" value={`${Math.round(fleet.data.active_vehicle_ratio * 100)}%`} tone="green" />
              <Card label="Idle vehicles" value={fleet.data.idle_vehicle_count} tone="orange" />
              <Card label="High-use vehicles" value={fleet.data.high_use_vehicles?.length || 0} tone="red" />
              <Card label="Utilization score" value={`${fleet.data.fleet_utilization_score}%`} />
            </div>
            <div className="viz-grid">
              <HorizontalBars title="Vehicle Utilization" data={utilization} color="#2563eb" />
              <DonutChart title="Fleet Status" data={statusSeries} />
              <DonutChart title="Vehicle Types" data={typeSeries} />
              <BarChart title="Estimated Distance Today" data={utilization.slice(0, 7)} unit="km" color="#0f9d8a" />
            </div>
          </>
        )}
      </Status>
      <Panel title="Preventive Check-Up Recommendation" icon={Truck}>
        <div className="control-row">
          <select value={vehicleId} onChange={(e) => setVehicleId(e.target.value)}>{shared.vehicles.map((v) => <option key={v.vehicle_id}>{v.vehicle_id}</option>)}</select>
          <Button onClick={checkVehicle} busy={busy} secondary>Analyze Vehicle</Button>
        </div>
        {maintenance && (
          <div className="gauge-grid">
            <GaugeCard label="Operational health" value={maintenance.health_score} unit="%" tone={riskTone(maintenance.risk_level)} />
            <GaugeCard label="Check-up window" value={maintenance.recommended_checkup_days} max={60} unit="d" tone="orange" />
            <Card label="Risk" value={maintenance.risk_level} tone={riskTone(maintenance.risk_level)} />
            <Card label="Provenance" value={maintenance.source} />
          </div>
        )}
      </Panel>
    </>
  );
}

function DataModels() {
  const models = useAsync(api.models, []);
  const providers = useAsync(api.providers, []);
  const training = useAsync(api.trainingData, []);
  const dataSources = useAsync(api.dataSources, []);
  const modelSeries = toSeries(countBy(models.data || [], (m) => m.availability));
  const providerSeries = toSeries(countBy(providers.data || [], (p) => p.source_type));
  return (
    <>
      <Header title="Data & Models" description="Technical transparency for provider health, model availability, training data, fallback logic, and provenance." />
      <Status {...models}>
        <>
          <div className="viz-grid">
            <DonutChart title="Model Availability" data={modelSeries.length ? modelSeries : [{ label: "loading", value: 1 }]} />
            <DonutChart title="Provider Source Mix" data={providerSeries.length ? providerSeries : [{ label: "demo", value: 1 }]} />
            <HorizontalBars title="Training Dataset Readiness" data={Object.entries(training.data || {}).map(([key, value]) => ({ label: key, value: safeNumber(value.rows || value.row_count || value.count || 1) }))} color="#7c3aed" />
            <HorizontalBars title="Data Source Count" data={Object.entries(dataSources.data || {}).map(([key, value]) => ({ label: key, value: Array.isArray(value) ? value.length : 1 }))} color="#0f9d8a" />
          </div>
          {providers.data && (
            <Panel title="Data Providers" icon={Network}>
              <div className="provider-grid">
                {providers.data.map((p) => (
                  <article className="provider-card" key={p.domain}>
                    <b>{p.domain}</b>
                    <span>{p.provider_name}</span>
                    <small>{p.health} / {p.source_type} / {p.latest_update || "seeded master data"}</small>
                  </article>
                ))}
              </div>
            </Panel>
          )}
          {models.data && (
            <Panel title="Model Registry" icon={Database}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Name</th><th>Version</th><th>Type</th><th>Availability</th><th>Metrics</th></tr></thead>
                  <tbody>{models.data.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.version}</td><td>{m.model_type}</td><td>{m.availability}</td><td><code>{JSON.stringify(m.metrics)}</code></td></tr>)}</tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      </Status>
    </>
  );
}

function App() {
  const [page, setPage] = useState("Overview");
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
          <div><strong>B.A.L.O.N</strong><span>Shipment Journey Intelligence</span></div>
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
          <small>Render backend / Vercel frontend ready</small>
        </div>
      </aside>
      <main>
        <Status {...bootstrap}>
          {page === "Overview" && <Overview shared={shared} />}
          {page === "Package Reports" && <PackageReports shared={shared} />}
          {page === "Analytics" && <Analytics />}
          {page === "Route Planning" && <RoutePlanning shared={shared} />}
          {page === "Fleet" && <Fleet shared={shared} />}
          {page === "Data & Models" && <DataModels />}
        </Status>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
