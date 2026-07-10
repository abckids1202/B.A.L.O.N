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

const navSections = [
  { label: "Operations", items: [["Overview", Activity], ["Live Operations", Play], ["Package Tracking", PackageSearch], ["Package Reports", ClipboardList], ["Hub Operations", Network], ["Route Planning", Route]] },
  { label: "Resources", items: [["Fleet & Vehicles", Truck], ["Analytics", BarChart3]] },
  { label: "System", items: [["Data, Models & Assumptions", Server]] }
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

function AppToolbar({ health, shipments = [], hubs = [] }) {
  const active = shipments.filter((shipment) => shipment.status === "Active").length;
  return (
    <div className="app-toolbar">
      <span><b>{health?.status || "ok"}</b> API</span>
      <span><b>{active}</b> active packages shown</span>
      <span><b>{hubs.length}</b> nodes</span>
      <span><b>{health?.timezone || "Asia/Jakarta"}</b> timezone</span>
    </div>
  );
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

const cachedRouteGeometry = [
  { label: "FC-JKT", lat: -6.2088, lon: 106.8456 },
  { label: "Cawang", lat: -6.242, lon: 106.872 },
  { label: "HUB-BKS", lat: -6.2383, lon: 106.9756 },
  { label: "Rawalumbu", lat: -6.2791, lon: 107.0021 },
  { label: "Bekasi Timur", lat: -6.2477, lon: 107.0188 }
];

function projectPoint(point, bounds = { minLat: -6.32, maxLat: -6.17, minLon: 106.82, maxLon: 107.08 }) {
  const x = 46 + ((point.lon - bounds.minLon) / (bounds.maxLon - bounds.minLon)) * 456;
  const y = 226 - ((point.lat - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * 178;
  return [Math.max(34, Math.min(506, x)), Math.max(36, Math.min(236, y))];
}

function pointsToPath(points) {
  return points.map((point, index) => {
    const [x, y] = projectPoint(point);
    return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function RouteMap({ candidates = [], progress = 62 }) {
  const best = candidates.find((candidate) => candidate.selected) || candidates[0];
  const current = candidates.find((candidate) => candidate.candidate_name === "Current");
  const bestCoords = best?.coordinates?.length ? best.coordinates.map((p) => ({ lat: p.lat, lon: p.lon, label: p.label })) : cachedRouteGeometry;
  const currentCoords = current?.coordinates?.length ? current.coordinates.map((p) => ({ lat: p.lat, lon: p.lon, label: p.label })) : cachedRouteGeometry;
  const packagePoint = bestCoords[Math.min(bestCoords.length - 1, Math.max(0, Math.floor((progress / 100) * (bestCoords.length - 1))))];
  const [px, py] = projectPoint(packagePoint);
  return (
    <div className="route-map geo">
      <svg viewBox="0 0 540 280" role="img" aria-label="Geographic route candidate map">
        <rect x="18" y="18" width="504" height="244" rx="12" />
        <path d={pointsToPath(currentCoords)} className="route-path muted" />
        <path d={pointsToPath(bestCoords)} className="route-path active" />
        {bestCoords.map((point, index) => {
          const [x, y] = projectPoint(point);
          return <g key={`${point.label}-${index}`} className="geo-stop"><circle cx={x} cy={y} r={index === 0 || index === bestCoords.length - 1 ? 11 : 8} /><text x={x + 10} y={y - 8}>{point.label}</text></g>;
        })}
        <g className="route-package"><circle cx={px} cy={py} r="10" /><text x={px + 12} y={py + 4}>Package</text></g>
      </svg>
      <div>
        <b>{best?.candidate_name || "Cached demo geometry"}</b>
        <span>{best ? `${best.metrics.distance_km.toFixed(1)} km / ${best.metrics.estimated_time_min.toFixed(0)} min / ${best.metrics.co2_kg.toFixed(2)} kg CO2e` : "Using deterministic Jakarta-Bekasi cached route geometry until optimization runs."}</span>
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


function TwinCard({ title, rows, tone = "blue" }) {
  return (
    <article className={`twin-card ${tone}`}>
      <h3>{title}</h3>
      {rows.map((row) => (
        <div key={row.label} className="twin-row">
          <span>{row.label}</span>
          <b>{row.value ?? "N/A"}</b>
        </div>
      ))}
    </article>
  );
}

function DigitalTwinPanel({ twin }) {
  if (!twin) {
    return <EmptyState>Build the package view to load the shipment digital twin.</EmptyState>;
  }
  const actual = twin.actual || {};
  const current = twin.current || {};
  const forecast = twin.forecast || {};
  const projected = twin.projected_final || {};
  return (
    <div className="twin-grid">
      <TwinCard title="Actual" tone="green" rows={[
        { label: "Elapsed", value: `${actual.elapsed_time_min ?? 0} min` },
        { label: "Completed distance", value: `${actual.distance_completed_km ?? 0} km` },
        { label: "Accumulated delay", value: `${actual.accumulated_delay_min ?? 0} min` },
        { label: "Carbon so far", value: `${actual.carbon_allocated_so_far_kg ?? 0} kg CO2e` }
      ]} />
      <TwinCard title="Current" rows={[
        { label: "Stage", value: current.stage_label },
        { label: "Location", value: current.location_id },
        { label: "Vehicle", value: current.vehicle_id || "N/A" },
        { label: "Hub dwell", value: current.hub ? `${current.hub.dwell_time_min} min` : "N/A" }
      ]} />
      <TwinCard title="Forecast" tone="orange" rows={[
        { label: "Predicted delay", value: `${forecast.predicted_delay_min ?? 0} min` },
        { label: "SLA breach risk", value: forecast.sla_breach_probability != null ? `${Math.round(forecast.sla_breach_probability * 100)}%` : "N/A" },
        { label: "Next milestone", value: forecast.next_milestone || "N/A" },
        { label: "Expected hub dwell", value: forecast.expected_next_hub_dwell_min != null ? `${forecast.expected_next_hub_dwell_min} min` : "N/A" }
      ]} />
      <TwinCard title="Projected Final" tone="red" rows={[
        { label: "Delivery ETA", value: projected?.delivery_eta || (actual.final_outcome?.delivered ? "Delivered" : "N/A") },
        { label: "SLA met probability", value: projected?.sla_met_probability != null ? `${Math.round(projected.sla_met_probability * 100)}%` : actual.final_outcome?.sla_status },
        { label: "Total journey time", value: projected?.projected_total_journey_time_min != null ? `${projected.projected_total_journey_time_min} min` : "Final" },
        { label: "Projected carbon", value: projected?.projected_total_carbon_kg != null ? `${projected.projected_total_carbon_kg} kg CO2e` : `${actual.carbon_allocated_so_far_kg ?? 0} kg CO2e` }
      ]} />
    </div>
  );
}

function VisualSignalCard({ signal }) {
  const payload = signal?.normalized_payload || {};
  const state = signal?.state_change || {};
  return (
    <article className={`signal-card ${riskTone(signal?.severity)}`}>
      <div>
        <StatusPill tone={riskTone(signal?.severity)}>{signal?.severity || "Info"}</StatusPill>
        <b>{String(signal?.signal_type || "Signal").replaceAll("_", " ")}</b>
      </div>
      <p>{state.affected_engines?.join(" -> ") || "Operational state updated"}</p>
      <small>{signal?.model_source || "Prototype engine"} / confidence {formatPercent(signal?.confidence || 0, 0)}</small>
      {payload.prototype_assumption && <small>{payload.prototype_assumption}</small>}
    </article>
  );
}

function VisualSignalStrip({ signals = [] }) {
  if (!signals.length) {
    return <EmptyState>No visual or predictive operational signal has been processed for this context yet.</EmptyState>;
  }
  return <div className="signal-grid">{signals.slice(0, 6).map((signal) => <VisualSignalCard key={signal.signal_id} signal={signal} />)}</div>;
}

function SignalStateSummary({ signals = [] }) {
  if (!signals.length) {
    return <EmptyState>No visual or predictive operational signal has been processed for this context yet.</EmptyState>;
  }
  const groups = Object.values(signals.reduce((acc, signal) => {
    const key = signal.signal_type;
    if (!acc[key]) acc[key] = { type: key, count: 0, latest: signal, maxConfidence: 0, severities: {} };
    acc[key].count += 1;
    acc[key].latest = signal;
    acc[key].maxConfidence = Math.max(acc[key].maxConfidence, signal.confidence || 0);
    acc[key].severities[signal.severity] = (acc[key].severities[signal.severity] || 0) + 1;
    return acc;
  }, {}));
  return (
    <div className="signal-state-grid">
      {groups.map((group) => {
        const topSeverity = Object.entries(group.severities).sort((a, b) => b[1] - a[1])[0]?.[0] || group.latest.severity;
        return (
          <article className={`signal-state ${riskTone(topSeverity)}`} key={group.type}>
            <span>{group.count} event{group.count === 1 ? "" : "s"}</span>
            <b>{group.type.replaceAll("_", " ")}</b>
            <strong>{formatPercent(group.maxConfidence, 0)}</strong>
            <small>{group.latest.state_change?.affected_engines?.slice(0, 2).join(" -> ") || group.latest.model_source}</small>
          </article>
        );
      })}
    </div>
  );
}

function InterventionQueue({ interventions, onAccept, onReject, busy }) {
  if (!interventions?.length) {
    return <EmptyState>No material operational intervention is active for this package.</EmptyState>;
  }
  return (
    <div className="intervention-list">
      {interventions.slice(0, 5).map((item) => (
        <article className="intervention-card" key={item.intervention_id}>
          <div>
            <b>{item.intervention_type.replaceAll("_", " ")}</b>
            <span>{item.status} / {item.severity}</span>
          </div>
          <p>{item.reason}</p>
          {item.impact && (
            <small>
              SLA {item.impact.actual_reforecast_sla_change_pp ?? item.impact.expected_sla_change_pp} pp /
              Delay {item.impact.actual_reforecast_delay_change_min ?? item.impact.expected_delay_change_min} min /
              CO2 {item.impact.actual_reforecast_co2_change_kg ?? item.impact.expected_co2_change_kg} kg
            </small>
          )}
          <div className="control-row">
            <Button secondary busy={busy} onClick={() => onAccept(item.intervention_id)}>Accept</Button>
            <Button secondary busy={busy} onClick={() => onReject(item.intervention_id)}>Reject</Button>
          </div>
        </article>
      ))}
    </div>
  );
}


function formatPercent(value, digits = 0) {
  return value == null ? "N/A" : `${(safeNumber(value) * 100).toFixed(digits)}%`;
}

function formatPp(value, digits = 1) {
  const n = safeNumber(value) * 100;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)} pp`;
}

function StatusPill({ children, tone = "blue" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function EntityTable({ columns, rows, selectedId, onSelect }) {
  return (
    <div className="table-wrap entity-table">
      <table>
        <thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id || row.shipment_id || row.vehicle_id || row.hub_id} className={selectedId === (row.id || row.shipment_id || row.vehicle_id || row.hub_id) ? "selected" : ""} onClick={() => onSelect?.(row)}>
              {columns.map((column) => <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function NetworkFlowCanvas({ shipments = [], hubs = [], interventions = [], mode: controlledMode }) {
  const [localMode, setLocalMode] = useState("flow");
  const mode = controlledMode || localMode;
  const active = shipments.filter((s) => s.status === "Active").length;
  const atRisk = shipments.filter((s) => s.priority === "Critical" || s.priority === "Express").length;
  const nodes = [
    { id: "FC-JKT", lane: "Origin", x: 44, y: 70, packages: Math.max(8, active * 3), risk: "Low", dwell: 12 },
    { id: "HUB-JKT", lane: "Main Hub", x: 202, y: 70, packages: 82, risk: "Critical", dwell: 83 },
    { id: "HUB-TNG", lane: "Main Hub", x: 202, y: 196, packages: 28, risk: "Medium", dwell: 29 },
    { id: "HUB-BKS", lane: "Local Hub", x: 360, y: 96, packages: 46, risk: atRisk ? "High" : "Medium", dwell: 37 },
    { id: "BEKASI LM", lane: "Last Mile", x: 518, y: 96, packages: 31, risk: "High", dwell: 18 },
    { id: "DEPOK LM", lane: "Last Mile", x: 518, y: 210, packages: 16, risk: "Low", dwell: 11 }
  ];
  const edges = [
    { from: "FC-JKT", to: "HUB-JKT", flow: 44, sla: 38, traffic: 48, carbon: 32, risk: "Low" },
    { from: "FC-JKT", to: "HUB-TNG", flow: 16, sla: 18, traffic: 28, carbon: 18, risk: "Low" },
    { from: "HUB-JKT", to: "HUB-BKS", flow: 46, sla: 82, traffic: 68, carbon: 58, risk: interventions.length ? "Intervention" : "High" },
    { from: "HUB-BKS", to: "BEKASI LM", flow: 31, sla: 67, traffic: 42, carbon: 24, risk: "High" },
    { from: "HUB-TNG", to: "DEPOK LM", flow: 16, sla: 21, traffic: 24, carbon: 20, risk: "Low" }
  ];
  const byId = Object.fromEntries(nodes.map((node) => [node.id, node]));
  const metric = { flow: "flow", sla: "sla", traffic: "traffic", carbon: "carbon" }[mode] || "flow";
  const label = { flow: "packages/hr", sla: "SLA exposure", traffic: "traffic pressure", carbon: "carbon flow" }[mode] || "packages/hr";
  return (
    <div className="flow-canvas ops-flow">
      {!controlledMode && (
        <div className="mode-tabs">
          {["flow", "sla", "traffic", "carbon"].map((item) => <button key={item} className={mode === item ? "active" : ""} onClick={() => setLocalMode(item)}>{item}</button>)}
        </div>
      )}
      <svg viewBox="0 0 660 320" role="img" aria-label="Network operations flow canvas">
        {["Origin", "Main Hub", "Local Hub", "Last Mile"].map((lane, index) => <g key={lane} className="flow-lane"><rect x={24 + index * 158} y="28" width="132" height="248" rx="10" /><text x={42 + index * 158} y="52">{lane}</text></g>)}
        {edges.map((edge) => {
          const a = byId[edge.from];
          const b = byId[edge.to];
          const pressure = edge[metric];
          const width = Math.max(5, Math.min(20, pressure / 5));
          return (
            <g key={`${edge.from}-${edge.to}`} className={`flow-edge ${edge.risk.toLowerCase()}`}>
              <path d={`M${a.x + 104} ${a.y + 35} C ${a.x + 138} ${a.y + 35}, ${b.x - 34} ${b.y + 35}, ${b.x} ${b.y + 35}`} style={{ strokeWidth: width }} />
              <text x={(a.x + b.x) / 2 + 28} y={(a.y + b.y) / 2 + 24}>{pressure}</text>
            </g>
          );
        })}
        {nodes.map((node) => (
          <g key={node.id} className={`flow-node-card ${riskTone(node.risk)}`} transform={`translate(${node.x}, ${node.y})`}>
            <rect width="112" height="70" rx="8" />
            <text x="10" y="20">{node.id}</text>
            <text x="10" y="42">{node.packages} pkg</text>
            <text x="10" y="60">{node.dwell}m dwell</text>
          </g>
        ))}
      </svg>
      <div className="flow-summary">
        <span>Mode: {label}</span>
        <span>Edge thickness = selected pressure</span>
        <span>Node cards = operational state</span>
        <span>Purple = active intervention corridor</span>
      </div>
    </div>
  );
}

function makeTrackingRows(shipments) {
  const stages = ["LINE_HAUL", "MAIN_HUB_PROCESSING", "INTER_HUB", "LOCAL_HUB_PROCESSING", "LAST_MILE", "ORIGIN_PROCESSING"];
  const locations = ["FC-JKT -> HUB-JKT", "HUB-JKT", "HUB-JKT -> HUB-BKS", "HUB-BKS", "Bekasi Timur", "FC-JKT"];
  const drivers = ["Andi Pratama", "Raka Wijaya", "Dimas Putra", "Maya Sari", "Bima Ardi"];
  return shipments.flatMap((shipment, baseIndex) => {
    const copies = shipments.length < 20 ? 8 : 1;
    return Array.from({ length: copies }, (_, offset) => {
      const index = baseIndex * copies + offset;
      const stage = stages[index % stages.length];
      const risk = shipment.priority === "Critical" ? .82 : shipment.priority === "Express" ? .61 : Math.max(.08, .18 + ((index * 7) % 58) / 100);
      const riskLevel = risk >= .7 ? "Critical" : risk >= .5 ? "High" : risk >= .3 ? "Medium" : "Low";
      const id = offset ? `${shipment.shipment_id}-${String(offset + 1).padStart(2, "0")}` : shipment.shipment_id;
      return {
        ...shipment,
        id,
        shipment_id: id,
        stage,
        stage_label: stage.replaceAll("_", " "),
        current_location: locations[index % locations.length],
        origin_label: index % 2 ? "FC-JKT-02" : "FC-JKT-01",
        destination_label: shipment.destination_zone,
        driver_name: drivers[index % drivers.length],
        eta: shipment.sla_deadline?.slice(11, 16) || "14:42",
        predicted_delay_min: Math.round(risk * 72),
        sla_probability: risk,
        risk_level: riskLevel,
        actual_carbon_kg: +(shipment.route_distance_km * (0.012 + (index % 4) * .002)).toFixed(2),
        projected_carbon_kg: +(shipment.route_distance_km * .052).toFixed(2),
        next_milestone: stage.includes("HUB") ? "HUB-BKS" : stage === "LAST_MILE" ? "Buyer" : "HUB-JKT",
        gps_age_seconds: 8 + (index % 9) * 11,
        last_updated: `${8 + index % 12} sec ago`,
        lat: -6.2088 - (index % 6) * .013,
        lon: 106.8456 + (index % 7) * .027,
        speed_kmh: stage.includes("HUB") || stage.includes("ORIGIN") ? 0 : 24 + (index % 8) * 3,
        route_progress: Math.min(96, 8 + (index * 13) % 88),
      };
    });
  });
}

function TrackingMap({ row }) {
  const route = cachedRouteGeometry;
  const progress = Math.max(0, Math.min(100, row?.route_progress || 40));
  const packagePoint = route[Math.min(route.length - 1, Math.floor((progress / 100) * (route.length - 1)))];
  const [px, py] = projectPoint(packagePoint);
  return (
    <div className="tracking-map">
      <svg viewBox="0 0 560 300" role="img" aria-label="Selected package geographic tracking map">
        <rect x="16" y="16" width="528" height="268" rx="12" />
        <path d={pointsToPath(route)} className="geo-route" />
        {route.map((point, index) => {
          const [x, y] = projectPoint(point);
          return <g key={point.label} className="geo-stop"><circle cx={x} cy={y} r={index === 0 || index === route.length - 1 ? 12 : 8} /><text x={x + 10} y={y - 8}>{point.label}</text></g>;
        })}
        <g className="map-package selected"><circle cx={px} cy={py} r="11" /><text x={px + 13} y={py + 4}>{row?.shipment_id || "Package"}</text></g>
        <text x="34" y="42">{progress}% route progress / GPS age {row?.gps_age_seconds || 0}s</text>
      </svg>
    </div>
  );
}

function OperationsMap({ shipments = [], hubs = [], selectedId }) {
  const coords = {
    "HUB-JKT": [245, 118],
    "HUB-BKS": [374, 142],
    "HUB-TNG": [116, 154],
    "FC-JKT": [190, 202],
    "Bekasi Timur": [430, 108]
  };
  const atRisk = shipments.filter((s) => s.priority === "Critical" || s.priority === "Express").length;
  return (
    <div className="ops-map">
      <svg viewBox="0 0 540 300" role="img" aria-label="Synthetic logistics network map">
        <rect x="18" y="18" width="504" height="264" rx="16" />
        <path d="M190 202 C224 150 256 122 245 118 C288 104 334 116 374 142" className="corridor active" />
        <path d="M116 154 C160 126 204 108 245 118" className="corridor" />
        <path d="M374 142 C402 126 420 116 430 108" className="corridor warning" />
        {hubs.map((hub) => {
          const [x, y] = coords[hub.hub_id] || [260, 150];
          return <g key={hub.hub_id} className="map-node hub"><circle cx={x} cy={y} r="15" /><text x={x + 18} y={y + 5}>{hub.hub_id}</text></g>;
        })}
        <g className="map-node fc"><circle cx="190" cy="202" r="13" /><text x="208" y="207">FC-JKT</text></g>
        <g className={selectedId === "SHP-1028" ? "map-package selected" : "map-package"}><circle cx="322" cy="132" r="10" /><text x="336" y="136">SHP-1028</text></g>
        <g className="map-cluster"><circle cx="418" cy="106" r="21" /><text x="410" y="111">{atRisk}</text></g>
      </svg>
      <div className="map-legend">
        <span><i className="blue" />Hub / FC</span>
        <span><i className="orange" />Traffic corridor</span>
        <span><i className="red" />SLA risk cluster</span>
      </div>
    </div>
  );
}

function ComparisonGrid({ impact }) {
  const current = impact?.current?.metrics || {};
  const best = impact?.recommended?.metrics || {};
  const cards = [
    ["Distance", current.distance_km, best.distance_km, "km"],
    ["Fuel", current.fuel_liter, best.fuel_liter, "L"],
    ["Estimated CO2e", current.co2_kg, best.co2_kg, "kg"],
    ["SLA Risk", current.sla_risk, best.sla_risk, "risk"]
  ];
  return (
    <div className="comparison-grid">
      {cards.map(([label, baseline, recommended, unit]) => {
        const delta = safeNumber(recommended) - safeNumber(baseline);
        const displayDelta = unit === "risk" ? formatPp(delta) : `${delta > 0 ? "+" : ""}${delta.toFixed(2)} ${unit}`;
        return (
          <article className="comparison-card" key={label}>
            <span>{label}</span>
            <b>{unit === "risk" ? formatPercent(baseline, 1) : `${baseline ?? 0} ${unit}`}</b>
            <strong>{unit === "risk" ? formatPercent(recommended, 1) : `${recommended ?? 0} ${unit}`}</strong>
            <small>{displayDelta}</small>
          </article>
        );
      })}
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
  const interventions = useAsync(() => api.interventions(), []);
  const riskSeries = toSeries(summary.data?.risk_distribution, { Critical: "Critical", High: "High", Medium: "Medium", Low: "Low" });
  const stageSeries = toSeries(countBy(shared.shipments, shipmentStage));
  const providerSeries = toSeries(countBy(providers.data || [], (p) => p.health));
  const attention = [
    ...shared.shipments.slice(0, 3).map((shipment) => ({ id: shipment.shipment_id, entity: shipment.shipment_id, stage: shipmentStage(shipment), problem: shipment.priority === "Critical" ? "Critical package priority" : "Watch active journey", severity: shipment.priority, action: "VIEW" })),
    ...(hubRisk.data || []).slice(0, 2).map((hub) => ({ id: hub.hub_id, entity: hub.hub_id, stage: "Hub", problem: hub.likely_bottleneck || "Congestion watch", severity: hub.risk_level, action: "VIEW HUB" }))
  ];
  return (
    <>
      <Header title="B.A.L.O.N Operations" description="Monitor shipment journeys, hub operations, route risk, fleet status, and logistics interventions across the synthetic logistics network." action={<span className="badge">Demo time {new Date().toLocaleTimeString()}</span>} />
      <Status {...summary}>
        {summary.data && (
          <>
            <div className="metrics-grid seven">
              <Card label="Active packages" value={summary.data.active_shipments} detail="current journeys" icon={PackageSearch} />
              <Card label="In transit" value={stageSeries.filter((s) => /transport|inter-hub/i.test(s.label)).reduce((a, b) => a + b.value, 0)} detail="moving packages" icon={Route} />
              <Card label="High / critical SLA" value={summary.data.predicted_delayed_shipments} detail="latest forecast" tone="orange" icon={AlertTriangle} />
              <Card label="Hub incidents" value={summary.data.critical_hub_count} detail="critical hubs" tone="red" icon={Network} />
              <Card label="Interventions" value={interventions.data?.length ?? 0} detail="active decisions" tone="orange" icon={Brain} />
              <Card label="CO2e today" value={`${summary.data.daily_carbon_estimate_kg} kg`} detail="projected routes" tone="green" icon={Gauge} />
              <Card label="Active vehicles" value={fleet.data?.active_vehicle_count ?? 0} detail={`${fleet.data?.total_vehicle_count ?? shared.vehicles.length} total`} icon={Truck} />
            </div>
            <div className="two-col overview-main">
              <Panel title="Network Operations Flow Canvas" icon={Map}>
                <NetworkFlowCanvas shipments={shared.shipments} hubs={shared.hubs} interventions={interventions.data || []} />
              </Panel>
              <Panel title="Packages / Incidents Needing Attention" icon={AlertTriangle}>
                <EntityTable columns={[
                  { key: "entity", label: "Entity" },
                  { key: "stage", label: "Stage" },
                  { key: "problem", label: "Problem" },
                  { key: "severity", label: "Severity", render: (row) => <StatusPill tone={riskTone(row.severity)}>{row.severity}</StatusPill> },
                  { key: "action", label: "Action" }
                ]} rows={attention} />
              </Panel>
            </div>
            <div className="viz-grid">
              <BarChart title="SLA Risk Distribution" data={riskSeries} color="#dc2626" />
              <HorizontalBars title="Shipment Journey Stage Distribution" data={stageSeries} color="#0f9d8a" />
              <HorizontalBars title="Hub Congestion Overview" data={(hubRisk.data || []).slice(0, 6).map((h) => ({ label: h.hub_id, value: h.congestion_score, color: riskTone(h.risk_level) === "red" ? "#dc2626" : "#f59e0b" }))} unit="/100" color="#f59e0b" />
              <DonutChart title="Provider Health" data={providerSeries.length ? providerSeries : [{ label: "healthy", value: 1 }]} />
              <DonutChart title="Fleet Status" data={toSeries({ Active: fleet.data?.active_vehicle_count || 0, Idle: fleet.data?.idle_vehicle_count || 0, Maintenance: fleet.data?.maintenance_vehicle_count || 0 })} />
              <BarChart title="Carbon by Journey Stage" data={[{ label: "Line haul", value: 44 }, { label: "Hub", value: 16 }, { label: "Inter-hub", value: 25 }, { label: "Last mile", value: 15 }]} unit="%" color="#0f9d8a" />
            </div>
            <Panel title="Recent Operations Activity" icon={ClipboardList}>
              <Timeline events={[
                ...(interventions.data || []).slice(0, 3).map((item) => ({ event_id: item.intervention_id, event_at: item.created_at, title: item.intervention_type.replaceAll("_", " "), description: item.reason, severity: item.severity })),
                ...summary.data.alerts.slice(0, 4).map((alert) => ({ event_id: alert.alert_id, event_at: alert.created_at, title: alert.title, description: alert.message, severity: alert.severity }))
              ]} />
            </Panel>
          </>
        )}
      </Status>
    </>
  );
}

function PackageTracking({ shared, onOpenPackage }) {
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState("All");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState("SHP-1028");
  const paged = useAsync(() => api.shipmentsPaged({ page, page_size: 60, q: search }), [page, search]);
  const sourceShipments = paged.data?.items?.length ? paged.data.items : shared.shipments.slice(0, 60);
  const rows = makeTrackingRows(sourceShipments)
    .filter((row) => stage === "All" || row.stage === stage)
    .sort((a, b) => b.sla_probability - a.sla_probability);
  const selected = rows.find((row) => row.shipment_id === selectedId) || rows[0];
  const totalRows = paged.data?.total || shared.shipments.length;
  const stages = ["All", ...new Set(makeTrackingRows(sourceShipments).map((row) => row.stage))];
  return (
    <>
      <Header title="Package Tracking" description="Monitor active package locations, ETA, journey progress, SLA exposure, and the next logistics milestone." action={<span className="badge">Last update 8 sec ago</span>} />
      <div className="metrics-grid">
        <Card label="Active packages" value={totalRows} detail={`${rows.length} shown`} />
        <Card label="In transit" value={rows.filter((r) => /HAUL|INTER_HUB/.test(r.stage)).length} />
        <Card label="At hub" value={rows.filter((r) => /HUB_PROCESSING/.test(r.stage)).length} />
        <Card label="Last mile" value={rows.filter((r) => /LAST_MILE/.test(r.stage)).length} />
        <Card label="High / critical SLA" value={rows.filter((r) => r.sla_probability >= 0.5).length} tone="orange" />
      </div>
      <Panel title="Package Operations Table" icon={ClipboardList}>
        <div className="toolbar">
          <input className="text-input" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search package ID" />
          <select value={stage} onChange={(event) => setStage(event.target.value)}>{stages.map((item) => <option key={item}>{item}</option>)}</select>
          <span>Server page {paged.data?.page || page} of {paged.data?.pages || 1}</span>
          <span>{totalRows} packages in network</span>
          <Button secondary busy={paged.loading} onClick={() => setPage(Math.max(1, page - 1))}>Prev</Button>
          <Button secondary busy={paged.loading} onClick={() => setPage(Math.min(paged.data?.pages || page + 1, page + 1))}>Next</Button>
        </div>
        <EntityTable columns={[
          { key: "shipment_id", label: "Package" },
          { key: "priority", label: "Priority" },
          { key: "status", label: "Status" },
          { key: "stage", label: "Stage", render: (row) => <StatusPill>{row.stage_label}</StatusPill> },
          { key: "current_location", label: "Current Location" },
          { key: "origin_label", label: "Origin" },
          { key: "destination_label", label: "Destination" },
          { key: "vehicle_id", label: "Vehicle" },
          { key: "driver_name", label: "Driver" },
          { key: "eta", label: "ETA" },
          { key: "predicted_delay_min", label: "Delay", render: (row) => `${row.predicted_delay_min} min` },
          { key: "sla_probability", label: "SLA Risk", render: (row) => <StatusPill tone={riskTone(row.risk_level)}>{formatPercent(row.sla_probability, 1)}</StatusPill> },
          { key: "actual_carbon_kg", label: "CO2 So Far", render: (row) => `${row.actual_carbon_kg.toFixed(2)} kg` },
          { key: "projected_carbon_kg", label: "Projected CO2", render: (row) => `${row.projected_carbon_kg.toFixed(2)} kg` },
          { key: "next_milestone", label: "Next" },
          { key: "last_updated", label: "Last Update" }
        ]} rows={rows} selectedId={selected?.shipment_id} onSelect={(row) => setSelectedId(row.shipment_id)} />
      </Panel>
      {selected && (
        <Panel title={`${selected.shipment_id} Tracking Digital Twin`} icon={PackageSearch}>
          <div className="entity-hero">
            <div><b>{selected.shipment_id}</b><span>{selected.stage_label}</span></div>
            <StatusPill tone={riskTone(selected.risk_level)}>{formatPercent(selected.sla_probability, 1)} SLA Risk / {selected.risk_level}</StatusPill>
            <span>{selected.current_location}</span>
            <span>{selected.vehicle_id} / {selected.driver_name}</span>
            <span>GPS {selected.gps_age_seconds} sec ago</span>
          </div>
          <div className="two-col map-first">
            <TrackingMap row={selected} />
            <div className="bento-grid">
              <TwinCard title="Current Tracking State" rows={[
                { label: "Coordinates", value: `${selected.lat.toFixed(4)}, ${selected.lon.toFixed(4)}` },
                { label: "Speed", value: `${selected.speed_kmh} km/h` },
                { label: "Route progress", value: `${selected.route_progress}%` },
                { label: "Next milestone", value: selected.next_milestone }
              ]} />
              <TwinCard title="Forecast" tone="orange" rows={[
                { label: "ETA", value: selected.eta },
                { label: "Predicted delay", value: `${selected.predicted_delay_min} min` },
                { label: "SLA buffer", value: `${Math.max(0, 90 - selected.predicted_delay_min)} min` },
                { label: "Traffic", value: selected.sla_probability > .5 ? "High" : "Normal" }
              ]} />
            </div>
          </div>
          <div className="control-row">
            <Button onClick={() => onOpenPackage(selected.shipment_id)}>Open Full Package Report</Button>
            <Button secondary>View Current Route</Button>
            <Button secondary>Follow in Live Operations</Button>
          </div>
        </Panel>
      )}
    </>
  );
}

function HubProcessFlow({ selected }) {
  const score = safeNumber(selected?.congestion_score);
  const steps = [
    { label: "Arrival", value: Math.max(12, score - 16) },
    { label: "Unloading", value: Math.max(10, score - 28) },
    { label: "Sorting", value: selected?.likely_bottleneck ? Math.min(96, score + 10) : Math.max(18, score - 35) },
    { label: "Staging", value: Math.max(16, score - 24) },
    { label: "Loading", value: Math.max(14, score - 38) },
    { label: "Departure", value: Math.max(10, 100 - score) }
  ];
  return (
    <div className="process-flow-ops">
      {steps.map((step) => <article key={step.label} className={step.value > 70 ? "hot" : step.value > 45 ? "warm" : ""}><b>{step.label}</b><i style={{ height: `${Math.max(12, step.value)}%` }} /><span>{Math.round(step.value)} pressure</span></article>)}
    </div>
  );
}

function HubOperations({ shared }) {
  const hubRisk = useAsync(api.hubRisk, []);
  const [selectedHub, setSelectedHub] = useState(shared.hubs[0]?.hub_id || "HUB-BKS");
  const [hubBusy, setHubBusy] = useState(false);
  const [hubRefresh, setHubRefresh] = useState(0);
  const signals = useAsync(() => api.operationalSignals(selectedHub), [selectedHub, hubRefresh]);
  const selected = (hubRisk.data || []).find((hub) => hub.hub_id === selectedHub) || (hubRisk.data || [])[0];
  const hubPackages = shared.shipments.filter((shipment) => shipment.origin_hub === selectedHub || selectedHub === "HUB-BKS");
  async function runHubSignal(kind) {
    setHubBusy(true);
    try {
      if (kind === "occupancy") await api.hubOccupancy(selectedHub);
      if (kind === "overflow") await api.hubOverflow(selectedHub);
      setHubRefresh((value) => value + 1);
    } finally {
      setHubBusy(false);
    }
  }
  return (
    <>
      <Header title="Hub Operations" description="Monitor hub queue pressure, dwell deviation, process bottlenecks, incidents, and affected packages." />
      <Status {...hubRisk}>
        <>
          <div className="metrics-grid">
            <Card label="Hubs" value={shared.hubs.length} />
            <Card label="Critical hubs" value={(hubRisk.data || []).filter((h) => h.risk_level === "Critical").length} tone="red" />
            <Card label="Affected packages" value={hubPackages.length} tone="orange" />
            <Card label="Selected hub pressure" value={selected ? `${selected.congestion_score}/100` : "N/A"} detail="composite congestion score" />
            <Card label="Likely bottleneck" value={selected?.likely_bottleneck || "None"} detail="highest process pressure" />
          </div>
          <div className="two-col">
            <Panel title="Hub Risk Table" icon={Network}>
              <EntityTable columns={[
                { key: "hub_id", label: "Hub" },
                { key: "risk_level", label: "Risk", render: (row) => <StatusPill tone={riskTone(row.risk_level)}>{row.risk_level}</StatusPill> },
                { key: "congestion_score", label: "Score", render: (row) => `${row.congestion_score}/100` },
                { key: "likely_bottleneck", label: "Bottleneck" },
                { key: "recommendation", label: "Recommendation" }
              ]} rows={(hubRisk.data || []).map((h) => ({ ...h, id: h.hub_id }))} selectedId={selectedHub} onSelect={(row) => setSelectedHub(row.hub_id)} />
            </Panel>
            <Panel title={`${selectedHub} Process Flow`} icon={Activity}>
              <div className="control-row">
                <Button secondary busy={hubBusy} onClick={() => runHubSignal("occupancy")}>Run Occupancy Signal</Button>
                <Button secondary busy={hubBusy} onClick={() => runHubSignal("overflow")}>Forecast Overflow</Button>
              </div>
              <HubProcessFlow selected={selected} />
              <HorizontalBars title="Process Pressure Components" data={[{ label: "Queue pressure", value: selected?.congestion_score || 0 }, { label: "Dwell excess", value: Math.max(0, (selected?.congestion_score || 0) - 20) }, { label: selected?.likely_bottleneck || "Bottleneck", value: selected?.likely_bottleneck ? Math.min(95, (selected?.congestion_score || 0) + 8) : 18 }, { label: "Outbound recovery", value: Math.max(8, 100 - (selected?.congestion_score || 0)) }]} color="#f59e0b" />
            </Panel>
          </div>
          <Panel title="Hub Visual and Forecast Signals" icon={Brain}>
            <Status {...signals}>
              <SignalStateSummary signals={signals.data || []} />
            </Status>
          </Panel>
          <Panel title="Affected Packages" icon={PackageSearch}>
            <EntityTable columns={[
              { key: "shipment_id", label: "Package" },
              { key: "priority", label: "Priority" },
              { key: "destination_zone", label: "Destination" },
              { key: "vehicle_id", label: "Vehicle" },
              { key: "status", label: "Status" }
            ]} rows={hubPackages.map((shipment) => ({ ...shipment, id: shipment.shipment_id }))} />
          </Panel>
        </>
      </Status>
    </>
  );
}



function LiveOperations({ shared }) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  const [speed, setSpeed] = useState("5x");
  const [playing, setPlaying] = useState(false);
  const [followMode, setFollowMode] = useState("Package");
  useEffect(() => { api.simulationState().then(setState).catch(() => null); }, []);
  async function action(fn, nextPlaying = playing) {
    setBusy(true);
    try {
      const next = await fn();
      setState(next);
      setPlaying(nextPlaying && !next.complete);
      return next;
    } finally {
      setBusy(false);
    }
  }
  async function startRuntime() {
    await api.simulationPlay();
    setPlaying(true);
  }
  async function pauseRuntime() {
    await api.simulationPause();
    setPlaying(false);
  }
  useEffect(() => {
    if (!playing || busy) return undefined;
    const delay = { "1x": 2400, "2x": 1600, "5x": 900, "10x": 520 }[speed] || 900;
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.simulationNext();
        setState(next);
        if (next.complete) {
          setPlaying(false);
          await api.simulationPause();
        }
      } catch {
        setPlaying(false);
      }
    }, delay);
    return () => window.clearTimeout(timer);
  }, [playing, busy, speed, state?.state?.current_step]);
  const processed = (state?.events || []).filter((event) => event.processed).length;
  const total = state?.events?.length || 0;
  const latest = state?.processed_event || (state?.events || []).filter((event) => event.processed).slice(-1)[0];
  return (
    <>
      <Header title="Live Operations" description="Replay the synthetic logistics network, process operational events, update package state, create interventions, and watch the network continue toward delivery." action={<span className="badge">Runtime {playing ? "Playing" : "Paused"} / {speed}</span>} />
      <div className="metrics-grid">
        <Card label="Runtime status" value={state?.state?.status || "Paused"} />
        <Card label="Demo step" value={state?.state?.current_step ?? 0} />
        <Card label="Events processed" value={`${processed}/${total}`} />
        <Card label="Focused package" value={state?.state?.active_shipment_id || "SHP-1028"} />
        <Card label="Alerts" value={state?.alerts?.length || 0} tone="orange" />
        <Card label="Visual signals" value={state?.visual_signals?.length || 0} tone="green" />
      </div>
      <Panel title="Replay Controls" icon={Play}>
        <div className="control-row">
          <Button secondary busy={busy} onClick={() => action(api.simulationReset, false)}>Reset</Button>
          {playing ? <Button secondary busy={busy} onClick={pauseRuntime}>Pause</Button> : <Button busy={busy} onClick={startRuntime}>Start</Button>}
          <Button secondary busy={busy} onClick={() => action(api.simulationNext, playing)}>Step</Button>
          <select value={speed} onChange={(event) => setSpeed(event.target.value)}><option>1x</option><option>2x</option><option>5x</option><option>10x</option></select>
          <select value={followMode} onChange={(event) => setFollowMode(event.target.value)}><option>Package</option><option>Hub</option><option>Route</option><option>Decision</option></select>
          <span className="muted">Autoplay repeatedly calls the same backend event processor used by manual Step.</span>
        </div>
      </Panel>
      <div className="two-col overview-main">
        <Panel title="Live Network Flow" icon={Map}>
          <NetworkFlowCanvas shipments={shared.shipments} hubs={shared.hubs} interventions={state?.alerts || []} mode={followMode === "Hub" ? "traffic" : followMode === "Route" ? "carbon" : followMode === "Decision" ? "sla" : "flow"} />
        </Panel>
        <Panel title="Latest Event Impact" icon={Activity}>
          {latest ? (
            <div className="event-impact">
              <StatusPill tone="orange">{latest.event_type || "EVENT"}</StatusPill>
              <h3>{latest.entity_id || "SHP-1028"}</h3>
              <p>{latest.payload?.description || "Operational event processed through the demo pipeline."}</p>
              <div className="comparison-grid">
                <article className="comparison-card"><span>Before</span><strong>Previous forecast</strong><small>stored in prediction history</small></article>
                <article className="comparison-card"><span>Event</span><strong>{latest.event_type || "Next event"}</strong><small>{latest.timestamp || state?.state?.current_timestamp}</small></article>
                <article className="comparison-card"><span>After</span><strong>State updated</strong><small>risk, route, hub and alerts refreshed</small></article>
                <article className="comparison-card"><span>Action</span><strong>{state?.route_recommendation?.candidate_name || "Monitor"}</strong><small>decision engine result</small></article>
              </div>
            </div>
          ) : <EmptyState>Reset or step the demo to process the first operational event.</EmptyState>}
        </Panel>
      </div>
      <div className="viz-grid">
        <BarChart title="Active Packages Over Demo Time" data={[{ label: "T0", value: 4 }, { label: "T1", value: 4 }, { label: "T2", value: 3 }, { label: "T3", value: 2 }]} color="#2563eb" />
        <BarChart title="High / Critical SLA Packages" data={[{ label: "T0", value: 1 }, { label: "T1", value: 2 }, { label: "T2", value: 3 }, { label: "T3", value: 1 }]} color="#dc2626" />
        <BarChart title="Interventions Created / Resolved" data={[{ label: "Created", value: Math.max(0, processed - 2) }, { label: "Resolved", value: Math.max(0, processed - 5) }]} color="#7c3aed" />
        <HorizontalBars title="Latest Signal Confidence" data={(state?.visual_signals || []).slice(0, 5).map((signal) => ({ label: signal.signal_type.replaceAll("_", " ").slice(0, 22), value: Math.round((signal.confidence || 0) * 100) }))} unit="%" color="#0f9d8a" />
      </div>
      <Panel title="Recent Event Stream" icon={ClipboardList}>
        <Timeline events={(state?.events || []).filter((event) => event.processed).slice(-8).map((event) => ({
          event_id: event.event_id,
          event_at: event.timestamp,
          title: event.event_type,
          description: event.payload?.description || `${event.entity_id} processed`,
          severity: event.payload?.severity || "Info"
        }))} />
      </Panel>
    </>
  );
}

function PackageReports({ shared }) {
  const [shipmentId, setShipmentId] = useState(shared.shipments[0]?.shipment_id || "SHP-1028");
  const [view, setView] = useState(null);
  const [twin, setTwin] = useState(null);
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
      const [journey, digitalTwin] = await Promise.all([api.packageJourneyView(id), api.digitalTwin(id)]);
      setView(journey);
      setTwin(digitalTwin);
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
        setTwin(next.digital_twin || await api.digitalTwin(shipmentId));
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
  const currentHubDwell = twin?.current?.hub ? `${twin.current.hub.dwell_time_min} min` : "N/A";
  const currentHubDetail = twin?.current?.hub ? `${twin.current.hub.dwell_excess_min ?? 0} min vs baseline` : "Not currently at a hub";

  async function acceptIntervention(interventionId) {
    setBusy(true);
    try {
      await api.acceptIntervention(interventionId);
      await loadView(shipmentId);
    } finally {
      setBusy(false);
    }
  }

  async function rejectIntervention(interventionId) {
    setBusy(true);
    try {
      await api.rejectIntervention(interventionId);
      await loadView(shipmentId);
    } finally {
      setBusy(false);
    }
  }

  async function runVisualSignal(kind) {
    setBusy(true);
    setError("");
    try {
      if (kind === "damage") await api.packageDamage(shipmentId);
      if (kind === "loading") await api.loadingValidation(shipmentId, "VAN-044");
      if (kind === "scenario") await api.visualDemoScenario();
      await loadView(shipmentId);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

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
      <Panel title="Shipment Journey Digital Twin" icon={Activity}>
        <DigitalTwinPanel twin={twin} />
      </Panel>
      <Panel title="Operational Intervention Queue" icon={AlertTriangle}>
        <InterventionQueue interventions={view?.active_interventions || twin?.active_interventions || []} onAccept={acceptIntervention} onReject={rejectIntervention} busy={busy} />
      </Panel>
      <Panel title="Visual Operational Signals" icon={Brain}>
        <div className="control-row">
          <Button secondary busy={busy} onClick={() => runVisualSignal("damage")}>Run Damage Scan</Button>
          <Button secondary busy={busy} onClick={() => runVisualSignal("loading")}>Validate Loading</Button>
          <Button busy={busy} onClick={() => runVisualSignal("scenario")}>Run Four-Signal Demo</Button>
          <span className="muted">Signals update package quality, hub context, forecasts, and interventions.</span>
        </div>
        <SignalStateSummary signals={[...(view?.visual_intelligence?.package_signals || []), ...(view?.visual_intelligence?.hub_signals || [])]} />
      </Panel>
      <div className="metrics-grid">
        <Card label="Current stage" value={view?.current_state?.stage_label || shipmentStage(shipment)} detail={view?.current_state?.location_id || shipment.current_status || "journey active"} />
        <Card label="Delay prediction" value={risk.predicted_delay_minutes != null ? `${risk.predicted_delay_minutes} min` : "n/a"} tone={riskTone(risk.sla_level)} />
        <Card label="SLA breach risk" value={risk.sla_probability != null ? `${Math.round(risk.sla_probability * 100)}%` : "n/a"} detail={risk.sla_level} tone={riskTone(risk.sla_level)} />
        <Card label="Traffic index" value={current.traffic_index ?? "n/a"} detail="latest provider snapshot" />
        <Card label="Current hub dwell" value={currentHubDwell} detail={currentHubDetail} />
        <Card label="Quality score" value={shipment.loading_compliance_score ?? "n/a"} detail={twin?.quality_context?.active_quality_hold ? "visual hold active" : "no active hold"} tone={twin?.quality_context?.active_quality_hold ? "red" : "green"} />
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
        <DonutChart title="Carbon Contribution by Journey Stage (%)" data={carbonData} />
        <BarChart title="Hub Processing Minutes" data={[
          { label: "Unload", value: hubVisit.unloading_time_min || 0 },
          { label: "Sort", value: hubVisit.sorting_time_min || 0 },
          { label: "Dwell", value: hubVisit.dwell_time_min || 0 },
          { label: "Load", value: hubVisit.loading_time_min || 0 }
        ]} color="#0f9d8a" />
        <HorizontalBars title="Route Decisions" data={(view?.route_decisions || []).slice(0, 5).map((route) => ({ label: route.candidate_name, value: route.metrics?.objective_score || route.metrics?.co2_kg || 0 }))} color="#2563eb" />
        <Heatmap title="Journey Risk Heatmap" rows={["Origin", "Hub", "Route", "Last mile"]} columns={["Delay", "SLA", "Carbon", "Visual"]} values={{ "Origin-Delay": 12, "Origin-SLA": 8, "Origin-Carbon": 22, "Origin-Visual": twin?.quality_context?.active_quality_hold ? 82 : 18, "Hub-Delay": Math.round(current.hub_dwell_excess_min || 0), "Hub-SLA": Math.round((risk.sla_probability || 0) * 100), "Hub-Carbon": 16, "Hub-Visual": Math.round((view?.visual_intelligence?.latest_hub_occupancy?.confidence || 0) * 100), "Route-Delay": Math.round((current.traffic_index || 0) * 100), "Route-SLA": Math.round((risk.sla_probability || 0) * 100), "Route-Carbon": 72, "Route-Visual": view?.visual_intelligence?.latest_wrong_loading ? 91 : 10, "Last mile-Delay": 31, "Last mile-SLA": 35, "Last mile-Carbon": 44, "Last mile-Visual": 24 }} />
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
  const [domain, setDomain] = useState("Network");
  const impact = summary.data?.route_impact || {};
  const comparison = {
    current: { metrics: { distance_km: 44.2, fuel_liter: 2.94, co2_kg: 1.65, sla_risk: 0.31 } },
    recommended: { metrics: { distance_km: 44.2 - safeNumber(impact.distance_reduction_km), fuel_liter: 2.94 - safeNumber(impact.fuel_reduction_liter), co2_kg: 1.65 - safeNumber(impact.co2_reduction_kg), sla_risk: 0.31 - safeNumber(impact.sla_risk_change) } }
  };
  return (
    <>
      <Header title="Analytics" description="Operational intelligence across Delivery, SLA, Hubs, Routes, Carbon & Cost, Fleet, and Forecast Quality." />
      <Status {...summary}>
        {summary.data && (
          <>
            <div className="metrics-grid">
              <Card label="Distance avoided" value={`${impact.distance_reduction_km ?? 0} km`} tone="green" />
              <Card label="Fuel avoided" value={`${impact.fuel_reduction_liter ?? 0} L`} tone="green" />
              <Card label="CO2e avoided" value={`${impact.co2_reduction_kg ?? 0} kg`} tone="green" />
              <Card label="SLA risk change" value={formatPp(-(impact.sla_risk_change ?? 0))} tone="orange" />
              <Card label="Critical hubs" value={summary.data.critical_hub_count} tone="red" />
            </div>
            <Panel title="Analytics Domain Navigator" icon={Brain}>
              <div className="mode-tabs domain-tabs">
                {["Network", "SLA", "Hub", "Route", "Carbon", "Fleet"].map((item) => <button key={item} className={domain === item ? "active" : ""} onClick={() => setDomain(item)}>{item}</button>)}
              </div>
              <ComparisonGrid impact={comparison} />
            </Panel>
            <div className="viz-grid">
              <BarChart title="Delay by Journey Stage" data={[{ label: "Origin", value: 9 }, { label: "Main hub", value: 42 }, { label: "Inter-hub", value: 31 }, { label: "Local hub", value: 18 }, { label: "Last mile", value: 24 }]} unit="m" color="#dc2626" />
              <DonutChart title="Carbon Contribution by Stage (%)" data={[{ label: "Line haul", value: 44 }, { label: "Hub", value: 16 }, { label: "Inter-hub", value: 25 }, { label: "Last mile", value: 15 }]} />
              <HorizontalBars title="Hub Dwell Pressure" data={(hubRisk.data || []).map((h) => ({ label: h.hub_id, value: h.congestion_score }))} unit="/100" color="#f59e0b" />
              <Heatmap title="Network Exposure Matrix" rows={["HUB-JKT", "HUB-BKS", "HUB-TGR", "LM-ZONE"]} columns={["Queue", "Dwell", "SLA", "Visual"]} values={{ "HUB-JKT-Queue": 71, "HUB-JKT-Dwell": 84, "HUB-JKT-SLA": 67, "HUB-JKT-Visual": 76, "HUB-BKS-Queue": 48, "HUB-BKS-Dwell": 56, "HUB-BKS-SLA": 42, "HUB-BKS-Visual": 35, "HUB-TGR-Queue": 25, "HUB-TGR-Dwell": 22, "HUB-TGR-SLA": 19, "HUB-TGR-Visual": 14, "LM-ZONE-Queue": 36, "LM-ZONE-Dwell": 30, "LM-ZONE-SLA": 51, "LM-ZONE-Visual": 44 }} />
              <HorizontalBars title="Operational Signal Mix" data={toSeries(summary.data.visual_signal_counts || {})} color="#0f9d8a" />
              <BarChart title="Forecast Quality Sample" data={[{ label: "On-time", value: 81 }, { label: "Late", value: 14 }, { label: "Reforecasted", value: 39 }, { label: "Improved", value: 22 }]} unit="%" color="#2563eb" />
              <div className="chart-card narrative">
                <h3>{domain} Detail</h3>
                <p>{summary.data.assumptions}</p>
                <p>SLA deltas are shown in percentage points. Carbon and fuel are displayed as separate physical units.</p>
                <div className="detail-table-mini">
                  {(summary.data.latest_visual_signals || []).slice(0, 4).map((signal) => <span key={signal.signal_id}><b>{signal.severity}</b>{signal.signal_type.replaceAll("_", " ")}</span>)}
                </div>
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
  const jobs = makeTrackingRows(shared.shipments).slice(0, 24).map((row, index) => ({
    ...row,
    id: `LEG-${row.shipment_id}-${String(index % 3 + 1).padStart(2, "0")}`,
    route_id: `RTE-${row.shipment_id}-${String(index % 3 + 1).padStart(2, "0")}`,
    job_type: row.stage.includes("LAST") ? "Last-mile batch" : "Transport leg",
    corridor: row.current_location.includes("->") ? row.current_location : `${row.origin_label} -> ${row.destination_label}`,
    active_jobs: 1 + (index % 4)
  }));
  const [selectedJobId, setSelectedJobId] = useState(jobs[0]?.id || "LEG-SHP-1028-02");
  const selected = jobs.find((job) => job.id === selectedJobId) || jobs[0];
  const [preset, setPreset] = useState("balanced_ai");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try {
      setResult(await api.optimize({ shipment_id: selected.shipment_id.split("-").slice(0, 2).join("-"), vehicle_id: selected.vehicle_id, preset }));
    } finally {
      setBusy(false);
    }
  }
  const candidates = result?.candidates || [];
  return (
    <>
      <Header title="Route Planning" description="Monitor active routing jobs, inspect current operating context, evaluate route trade-offs, and activate operational decisions." />
      <Panel title="Routing Jobs Table" icon={Route}>
        <EntityTable columns={[
          { key: "id", label: "Job" },
          { key: "shipment_id", label: "Package" },
          { key: "job_type", label: "Type" },
          { key: "corridor", label: "Corridor" },
          { key: "vehicle_id", label: "Vehicle" },
          { key: "driver_name", label: "Driver" },
          { key: "sla_probability", label: "SLA Risk", render: (row) => <StatusPill tone={riskTone(row.risk_level)}>{formatPercent(row.sla_probability, 1)}</StatusPill> },
          { key: "predicted_delay_min", label: "Delay", render: (row) => `${row.predicted_delay_min} min` },
          { key: "route_id", label: "Route" }
        ]} rows={jobs} selectedId={selected?.id} onSelect={(row) => { setSelectedJobId(row.id); setResult(null); }} />
      </Panel>
      {selected && (
        <Panel title={`${selected.id} Routing Job Digital Twin`} icon={Map}>
          <div className="entity-hero">
            <div><b>{selected.id}</b><span>{selected.corridor}</span></div>
            <StatusPill tone={riskTone(selected.risk_level)}>{selected.risk_level}</StatusPill>
            <span>{selected.vehicle_id} / {selected.driver_name}</span>
            <span>{selected.route_id}</span>
          </div>
          <div className="control-grid">
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              <option value="balanced_ai">Balanced AI</option>
              <option value="fastest">Time Priority</option>
              <option value="greenest">Green Priority</option>
              <option value="sla_priority">SLA Priority</option>
            </select>
            <Button onClick={run} busy={busy}>Evaluate Routes</Button>
          </div>
        </Panel>
      )}
      <div className="two-col map-first">
        <Panel title="Route Map" icon={Map}><RouteMap candidates={candidates} /></Panel>
        <Panel title="Methodology" icon={Database}>
          <div className="method-list">
            <p><b>Road network:</b> Haversine demo matrix fallback, not live road routing.</p>
            <p><b>Traffic:</b> Jakarta Prototype Traffic Model.</p>
            <p><b>Cost:</b> fuel/energy demo price snapshots.</p>
            <p><b>Carbon:</b> CF-DEMO-2026 deterministic baseline.</p>
          </div>
        </Panel>
      </div>
      {result && (
        <Panel title="Candidate Trade-Off Table" icon={BarChart3}>
          <EntityTable columns={[
            { key: "candidate_name", label: "Candidate" },
            { key: "distance", label: "Distance", render: (row) => `${row.metrics.distance_km.toFixed(1)} km` },
            { key: "time", label: "Time", render: (row) => `${row.metrics.estimated_time_min.toFixed(0)} min` },
            { key: "fuel", label: "Fuel", render: (row) => `${row.metrics.fuel_liter.toFixed(2)} L` },
            { key: "co2", label: "CO2e", render: (row) => `${row.metrics.co2_kg.toFixed(2)} kg` },
            { key: "sla", label: "SLA Risk", render: (row) => <StatusPill tone={riskTone(row.metrics.sla_risk > .5 ? "High" : "Low")}>{formatPercent(row.metrics.sla_risk, 1)}</StatusPill> },
            { key: "score", label: "Score", render: (row) => row.metrics.objective_score }
          ]} rows={candidates.map((candidate) => ({ ...candidate, id: candidate.candidate_name }))} />
        </Panel>
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
  const usage = fleet.data?.vehicle_usage || [];
  const selectedVehicle = shared.vehicles.find((v) => v.vehicle_id === vehicleId) || {};
  return (
    <>
      <Header title="Fleet & Vehicles" description="Track vehicle utilization, driver context, active package assignments, distance, fuel or energy cost, carbon, and preventive check-up recommendations." />
      <Status {...fleet}>
        {fleet.data && (
          <>
            <div className="metrics-grid">
              <Card label="Total vehicles" value={fleet.data.total_vehicle_count} />
              <Card label="Active vehicles" value={fleet.data.active_vehicle_count} tone="green" />
              <Card label="Idle vehicles" value={fleet.data.idle_vehicle_count} tone="orange" />
              <Card label="Average utilization" value={formatPercent(fleet.data.average_utilization_ratio)} />
              <Card label="High-use vehicles" value={fleet.data.high_use_vehicles?.length || 0} tone="red" />
            </div>
            <div className="viz-grid">
              <HorizontalBars title="Vehicle Utilization" data={usage.map((u) => ({ label: u.vehicle_id, value: Math.round(u.utilization_ratio * 100) }))} unit="%" color="#2563eb" />
              <DonutChart title="Fleet Status" data={toSeries({ Active: fleet.data.active_vehicle_count, Idle: fleet.data.idle_vehicle_count, Maintenance: fleet.data.maintenance_vehicle_count, Unavailable: fleet.data.unavailable_vehicle_count })} />
              <BarChart title="Distance Today" data={usage.map((u) => ({ label: u.vehicle_id, value: u.distance_today_km }))} unit="km" color="#0f9d8a" />
            </div>
            <Panel title="Vehicle Operations Table" icon={Truck}>
              <EntityTable columns={[
                { key: "vehicle_id", label: "Vehicle" },
                { key: "status", label: "Status", render: (row) => <StatusPill tone={row.status === "Active" ? "green" : "orange"}>{row.status}</StatusPill> },
                { key: "shipment_count", label: "Packages" },
                { key: "utilization_ratio", label: "Utilization", render: (row) => formatPercent(row.utilization_ratio) },
                { key: "load_utilization", label: "Load", render: (row) => formatPercent(row.load_utilization) },
                { key: "distance_today_km", label: "Distance" , render: (row) => `${row.distance_today_km} km` },
                { key: "active_operating_minutes", label: "Active min" }
              ]} rows={usage.map((u) => ({ ...u, id: u.vehicle_id }))} selectedId={vehicleId} onSelect={(row) => setVehicleId(row.vehicle_id)} />
            </Panel>
          </>
        )}
      </Status>
      <Panel title={`${vehicleId} Vehicle Digital Twin`} icon={Truck}>
        <div className="twin-grid">
          <TwinCard title="Assignment" rows={[{ label: "Driver", value: vehicleId.startsWith("MTR") ? "Courier Dimas" : "Driver Raka" }, { label: "Current package", value: shared.shipments.find((s) => s.vehicle_id === vehicleId)?.shipment_id || "None" }, { label: "Status", value: selectedVehicle.status || "N/A" }]} />
          <TwinCard title="Utilization" tone="green" rows={[{ label: "Active minutes", value: `${usage.find((u) => u.vehicle_id === vehicleId)?.active_operating_minutes || 0} min` }, { label: "Available minutes", value: `${usage.find((u) => u.vehicle_id === vehicleId)?.available_operating_minutes || 0} min` }, { label: "Distance today", value: `${usage.find((u) => u.vehicle_id === vehicleId)?.distance_today_km || 0} km` }]} />
          <TwinCard title="Cost / Carbon" tone="orange" rows={[{ label: "Fuel or energy", value: selectedVehicle.fuel_type || "N/A" }, { label: "Efficiency", value: `${selectedVehicle.fuel_efficiency_km_per_liter || 0} km/L` }, { label: "Estimated cost", value: "Rp87,040" }]} />
          <TwinCard title="Maintenance" tone="red" rows={[{ label: "Last service", value: selectedVehicle.last_service_date || "N/A" }, { label: "Current KM", value: selectedVehicle.current_km || 0 }, { label: "Next action", value: maintenance?.risk_level || "Check when selected" }]} />
        </div>
        <div className="control-row"><Button onClick={checkVehicle} busy={busy} secondary>Analyze Preventive Check-Up</Button></div>
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
      <Header title="Data, Models & Assumptions" description="Technical transparency for providers, model runtime state, traffic assumptions, fuel and energy prices, carbon factors, hub baselines, and SLA thresholds." />
      <Status {...models}>
        <>
          <div className="viz-grid">
            <DonutChart title="Model Availability" data={modelSeries.length ? modelSeries : [{ label: "loading", value: 1 }]} />
            <DonutChart title="Provider Source Mix" data={providerSeries.length ? providerSeries : [{ label: "demo", value: 1 }]} />
            <HorizontalBars title="Training Dataset Readiness" data={Object.entries(training.data || {}).map(([key, value]) => ({ label: key, value: safeNumber(value.rows || value.row_count || value.count || 1) }))} color="#7c3aed" />
            <HorizontalBars title="Provider Freshness" data={(providers.data || []).map((p) => ({ label: p.domain, value: p.available ? 100 : 0 }))} unit="%" color="#0f9d8a" />
          </div>
          <Panel title="Operational Assumptions Registry" icon={Database}>
            <div className="assumption-grid">
              <article><b>Route / TMS provider</b><span>DemoRouteProvider / Haversine demo matrix fallback</span></article>
              <article><b>Traffic model</b><span>Jakarta Prototype Traffic Profile / synthetic multipliers</span></article>
              <article><b>Fuel prices</b><span>Diesel Rp6,800/L, gasoline Rp10,000/L</span></article>
              <article><b>Energy price</b><span>EV charging Rp1,444/kWh</span></article>
              <article><b>Carbon factors</b><span>CF-DEMO-2026, deterministic baseline</span></article>
              <article><b>Hub baselines</b><span>Hub normal dwell profiles from seeded hub table</span></article>
              <article><b>Visual signals</b><span>Prototype engines write normalized operational signals before updating twins and interventions</span></article>
              <article><b>SLA thresholds</b><span>Low / Medium / High / Critical probability bands</span></article>
            </div>
          </Panel>
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
                  <tbody>{models.data.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.version}</td><td>{m.model_type}</td><td><StatusPill tone={m.availability === "AVAILABLE" ? "green" : "orange"}>{m.availability}</StatusPill></td><td><code>{m.fallback_state || JSON.stringify(m.metrics)}</code></td></tr>)}</tbody>
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
    const [health, shipmentPage, vehiclePage, hubs, network] = await Promise.all([api.health(), api.shipmentsPaged({ page: 1, page_size: 120 }), api.vehiclesPaged({ page: 1, page_size: 120 }), api.hubs(), api.networkSummary()]);
    return { health, shipments: shipmentPage.items || [], vehicles: vehiclePage.items || [], hubs, network };
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
          {navSections.map((section) => (
            <div className="nav-section" key={section.label}>
              <span>{section.label}</span>
              {section.items.map(([label, Icon]) => (
                <button key={label} className={page === label ? "active" : ""} onClick={() => setPage(label)}>
                  <Icon size={18} /> {label}
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>API</span>
          <b>{api.base}</b>
          <small>Render backend / Vercel frontend ready</small>
        </div>
      </aside>
      <main>
        <AppToolbar health={shared.health} shipments={shared.shipments} hubs={shared.hubs} />
        <Status {...bootstrap}>
          {page === "Overview" && <Overview shared={shared} />}
          {page === "Live Operations" && <LiveOperations shared={shared} />}
          {page === "Package Tracking" && <PackageTracking shared={shared} onOpenPackage={(id) => setPage("Package Reports")} />}
          {page === "Package Reports" && <PackageReports shared={shared} />}
          {page === "Hub Operations" && <HubOperations shared={shared} />}
          {page === "Route Planning" && <RoutePlanning shared={shared} />}
          {page === "Fleet & Vehicles" && <Fleet shared={shared} />}
          {page === "Analytics" && <Analytics />}
          {page === "Data, Models & Assumptions" && <DataModels />}
        </Status>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
