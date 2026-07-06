# LogiSense AI — UI/UX Style Guide

**Version:** 1.0  
**Applies to:** Streamlit frontend  
**Product character:** modern logistics command center

---

## 1. Visual Concept

The interface should communicate:

- operational control;
- predictive intelligence;
- environmental awareness;
- urgency without visual chaos;
- technical credibility.

The visual metaphor is a **logistics control tower**.

The app should not feel like:

- a generic Streamlit tutorial;
- a student CRUD dashboard;
- a cyberpunk interface;
- a marketing landing page.

The app should feel like:

- an operations console;
- a fleet/network dashboard;
- a decision-support platform.

---

## 2. Brand Direction

Working product name:

**LogiSense AI**

Descriptor:

**Green & Resilient Logistics Command Center**

Do not use Blibli brand assets or imply an official Blibli product unless permission is explicitly available.

Competition context may be mentioned in documentation.

---

## 3. Color System

### Core colors

| Token | Hex | Purpose |
|---|---|---|
| `--bg-app` | `#F4F7FB` | Main application background |
| `--bg-surface` | `#FFFFFF` | Cards and panels |
| `--bg-sidebar` | `#0F172A` | Sidebar |
| `--primary` | `#2563EB` | Main action / active navigation |
| `--primary-dark` | `#1D4ED8` | Hover / emphasis |
| `--secondary` | `#5B5BD6` | AI/optimization accent |
| `--teal` | `#0F9D8A` | Green logistics accent |
| `--text-main` | `#0F172A` | Main text |
| `--text-muted` | `#64748B` | Secondary text |
| `--border` | `#E2E8F0` | Borders |
| `--grid` | `#EEF2F7` | Chart grid / separators |

### Status colors

| Status | Hex |
|---|---|
| Safe / Normal / Low | `#16A34A` |
| Watch / Medium | `#D97706` |
| High | `#EA580C` |
| Critical | `#DC2626` |
| Info | `#2563EB` |
| Simulation | `#7C3AED` |
| Synthetic data | `#6D28D9` |

Never communicate risk by color alone. Always include a text label and, when useful, an icon.

---

## 4. Typography

Preferred font stack:

```css
font-family:
"Inter",
"Segoe UI",
"Helvetica Neue",
Arial,
sans-serif;
```

### Type hierarchy

| Style | Size | Weight |
|---|---:|---:|
| Page title | 30–36 px | 700 |
| Section title | 20–24 px | 650–700 |
| Card metric | 26–34 px | 700 |
| Card label | 12–14 px | 600 |
| Body | 14–16 px | 400 |
| Helper text | 12–13 px | 400 |
| Table text | 12–14 px | 400–500 |

Use sentence case for normal headings.

Avoid all-caps paragraphs.

All-caps is acceptable for compact status labels such as `CRITICAL`.

---

## 5. Spacing System

Use an 8 px base system.

Recommended tokens:

```text
4 px   micro
8 px   xs
12 px  sm
16 px  md
24 px  lg
32 px  xl
48 px  2xl
```

Page horizontal padding:

- desktop: 24–36 px.

Card gap:

- 16 px.

Section gap:

- 24–32 px.

Avoid large empty spaces between dashboard sections.

---

## 6. Grid and Layout

Use wide Streamlit layout.

Primary page grid:

```text
12-column mental model
```

Common layouts:

- 4 KPI cards: 3 columns each;
- main chart 8 columns + alert panel 4 columns;
- map 8 columns + recommendation 4 columns;
- two equal analysis panels: 6 + 6.

Avoid more than six small KPI cards in one row.

At narrow widths, allow Streamlit columns to stack naturally.

---

## 7. Navigation

Use a dark sidebar.

Navigation order:

1. Command Center
2. Delivery Risk AI
3. Green Route Optimizer
4. Network Resilience
5. Live Simulation
6. Analytics & Impact
7. Data & Models
8. Reports

Sidebar footer:

```text
Prototype Environment
Synthetic / Simulated Data
```

The active page must be visually clear.

Do not use random emojis as page names.

A single consistent icon set may be used.

---

## 8. Page Header

Each page begins with:

- title;
- one-sentence operational description;
- environment badge when demo data is active.

Example:

```text
Delivery Risk AI
Predict delay and SLA breach risk from current shipment conditions.

[SYNTHETIC DEMO ENVIRONMENT]
```

Do not repeat the product logo at the top of every section.

---

## 9. KPI Cards

A KPI card contains:

- compact label;
- large value;
- optional delta;
- optional context line.

Example:

```text
HIGH SLA RISK
38
+9 since previous simulation step
```

Rules:

- white surface;
- 1 px border;
- 12–16 px radius;
- subtle shadow;
- no strong gradients;
- metric value left aligned.

For risk cards, use a 3–4 px status accent line.

---

## 10. Status Badges

Badge shape:

- rounded pill;
- 11–12 px semibold;
- 6 px vertical padding;
- 10 px horizontal padding.

Examples:

```text
LOW
MEDIUM
HIGH
CRITICAL
DEMO MODE
SYNTHETIC
ML MODEL
RULE FALLBACK
```

Risk badge text must remain readable in grayscale context through explicit words.

---

## 11. Buttons

### Primary

Use for:

- Run Prediction
- Optimize Routes
- Advance Simulation
- Save Recommendation
- Generate Summary

Primary color.

Only one dominant primary CTA per panel.

### Secondary

Use for:

- Reset
- Export
- View History
- Compare

White or light surface with border.

### Destructive / critical

Use sparingly.

Do not make alerts themselves look like destructive buttons.

---

## 12. Forms

Forms should be grouped by task.

Use labels that describe data meaning.

Good:

```text
Traffic Congestion Index
```

Bad:

```text
traffic_idx
```

Show units in labels:

```text
Load Weight (kg)
Hub Dwell Time (min)
Distance (km)
```

Advanced model/policy settings should live inside an expander.

Do not expose every configuration variable by default.

---

## 13. File Upload Areas

Upload area must show:

- supported file type;
- purpose;
- sample file link when available;
- max file guidance.

Example:

```text
Upload shipment batch
CSV · required columns documented below

[Download sample CSV]
```

After upload:

- show row count;
- show validation status;
- show invalid rows separately.

Never silently discard invalid data.

---

## 14. Tables

Tables should be used for operational lists.

Examples:

- shipment risk table;
- alert feed;
- route candidate table;
- hub risk table;
- model registry.

Rules:

- freeze or emphasize ID/status columns where practical;
- round displayed numeric values;
- keep raw precision in data/export;
- risk level next to probability;
- use human-readable timestamps;
- sort highest operational risk first by default.

---

## 15. Charts

Preferred library:

Plotly.

### Use cases

Line chart:

- SLA risk over simulation time;
- hub dwell trend;
- queue size trend;
- health score trend.

Bar chart:

- route objective comparison;
- CO₂ by route;
- vehicle utilization.

Stacked bar:

- shipments by SLA risk level.

Heatmap:

- hub risk by hour and hub;
- risk intensity.

Scatter:

- predicted versus actual delay in model evaluation.

### Chart rules

- descriptive title;
- axis units;
- hover tooltips;
- no 3D charts;
- no pie chart with more than five segments;
- legend must be visible when multiple series exist;
- synthetic/demo label outside chart when data is synthetic.

---

## 16. Maps

Maps are a core feature.

Route map must show:

- origin/depot;
- numbered stops;
- current route;
- selected candidate route;
- hubs;
- vehicle position in simulation.

Use line styling to differentiate route candidates.

Do not rely only on color; use route labels and legend.

Hub map may show:

- marker size for volume;
- risk badge in tooltip;
- congestion score;
- dwell time.

---

## 17. Risk Panels

### SLA risk panel

Display:

- probability;
- risk level;
- predicted delay;
- SLA buffer;
- top factors;
- timestamp.

### Hub risk panel

Display:

- congestion score;
- risk level;
- queue growth;
- dwell excess;
- likely bottleneck;
- estimated shipment impact.

### Fleet resilience panel

Display:

- utilization;
- high-use vehicles;
- underused vehicles;
- maintenance attention count.

---

## 18. AI Provenance Labels

Every AI output must show its source.

Examples:

```text
Delay Prediction
XGBoost Regressor · v1.2

SLA Risk
Random Forest Classifier · v1.0

Carbon Estimate
Deterministic Carbon Baseline

Maintenance Risk
Rule Fallback
```

When model is unavailable:

```text
MODEL NOT AVAILABLE
Using Rule Fallback
```

Never silently switch prediction sources.

---

## 19. Synthetic Data Disclosure

Global badge:

```text
SYNTHETIC DEMO ENVIRONMENT
```

Model panel disclosure:

```text
Prototype models may be trained on synthetic logistics labels.
Displayed evaluation metrics measure performance against the current
prototype dataset and are not validated production logistics metrics.
```

Do not bury this in a footer.

---

## 20. Alerts

Alert card structure:

```text
[CRITICAL] SLA BREACH RISK
Shipment SHP-1028
Risk increased from 42% to 81%.

Main trigger:
Hub dwell time +42 min

Recommendation:
Review Balanced AI Route.

12:42 WIB
```

Alert feed defaults to:

1. Critical
2. Warning
3. Watch
4. Info

Acknowledged alerts remain in history.

---

## 21. Loading States

Use action-specific text.

Good:

```text
Scoring current SLA risk...
Evaluating 150 route candidates...
Recalculating hub congestion...
```

Bad:

```text
Loading...
```

Long operations should show a spinner and explanatory text.

---

## 22. Empty States

Every empty state answers:

1. What is missing?
2. What should the user do?

Example:

```text
No shipment selected

Select a shipment from the control panel to view
delay and SLA risk analysis.
```

Do not show blank charts.

---

## 23. Error States

Errors should be readable and actionable.

Example:

```text
Route optimization failed

The selected vehicle capacity is below the total shipment load.
Choose another vehicle or split the delivery batch.
```

Do not show a Python traceback to users.

Developer logs may contain stack traces.

---

## 24. Command Center Layout

Recommended:

```text
HEADER
Environment badge + simulation state

ROW 1
Active Shipments | High SLA Risk | Critical Hubs | CO₂ Today | Fleet Utilization

ROW 2
Risk Map / Route Map                 | Critical Alerts

ROW 3
SLA Risk Trend                       | Hub Congestion Heatmap

ROW 4
Route / Carbon Performance           | Fleet Utilization

ROW 5
Recent Decision Engine Recommendations
```

---

## 25. Delivery Risk Page Layout

```text
Shipment Selection + Current Context

Loading Risk Panel
Image / Annotated Result | Compliance / Warnings

Delay & SLA Panel
Predicted Delay | SLA Risk | Buffer | Model Source

Main Factors

Prediction History

Generated Alerts
```

---

## 26. Route Optimizer Layout

```text
Delivery Batch + Vehicle + Capacity

Decision Policy
Fastest | Greenest | SLA Priority | Balanced AI

Advanced Weights

Route Candidate Comparison

Interactive Map

AI Recommendation Panel

Carbon Comparison

Save Recommendation
```

---

## 27. Network Resilience Layout

```text
Hub Risk Overview + Heatmap

Selected Hub
Congestion Score | Queue Growth | Dwell Excess | Likely Bottleneck

Hub Time-Series Charts

Fleet Utilization

Vehicle Resilience / Preventive Check-Up Panel
```

---

## 28. Simulation Page Layout

```text
Simulation Controls
Reset | Previous State | Next Event | Auto Play | Pause

Current Simulation Timestamp

Event Stream

Current Shipment State

Before vs After Risk

Before vs After Route Recommendation

Generated Alerts
```

---

## 29. Analytics Page Layout

```text
Baseline Selector + Analysis Period

Impact KPI Cards
Distance | Fuel | CO₂ | SLA Risk

Route Comparison

Carbon Trend

Fleet Utilization Insights

Business Impact Assumptions

Model Performance Summary
```

---

## 30. UI Acceptance Criteria

The style guide is implemented successfully when:

- all pages share one visual system;
- users can identify risk level without reading chart details;
- synthetic data is always visible as synthetic;
- route recommendation is visually distinct from route candidates;
- AI source is visible;
- no page looks like a default Streamlit example;
- maps and heatmaps have legends;
- every major action has loading, success, and error states;
- no final MVP button is non-functional.
