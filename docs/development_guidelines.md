# LogiSense AI — Development Guidelines

## 1. Source of Truth

Priority order:

1. approved PRD;
2. architecture document;
3. workflow document;
4. task plan;
5. implementation plan;
6. code.

If code conflicts with PRD, stop and document the conflict.

Do not silently change product scope.

---

## 2. Core Coding Rules

Use:

- Python type hints;
- small functions;
- Pydantic request/response schemas;
- dataclasses where suitable for internal domain values;
- centralized config;
- explicit exceptions;
- structured logging;
- deterministic seeds;
- pytest.

Avoid:

- monolithic files;
- global mutable state;
- copied formulas;
- raw SQL in services;
- business logic in Streamlit pages;
- business logic in FastAPI routes;
- silent `except Exception: pass`;
- hardcoded metrics.

---

## 3. AI Honesty Rules

Never:

- fake mAP;
- fake F1;
- fake RMSE;
- fake CO₂ reduction;
- call synthetic metrics real-world performance;
- claim guaranteed SLA prevention;
- claim exact mechanical failure prediction;
- call rules AI when they are deterministic rules.

Always display:

- model source;
- model version;
- dataset type;
- fallback status;
- synthetic-target disclosure.

---

## 4. Synthetic Data Rules

Synthetic data must:

- use a fixed seed;
- have documented generation logic;
- be reproducible;
- be labeled synthetic in UI and docs;
- include normal and failure/risk cases.

Synthetic labels may be used for pipeline demonstration.

Metrics on synthetic labels must be described as:

> performance against the prototype synthetic target logic.

---

## 5. Model Selection Rules

Do not choose a model because it sounds advanced.

For each supervised task:

1. create baseline;
2. train candidate models;
3. use validation split;
4. compare appropriate metrics;
5. select best justified model;
6. evaluate once on test data;
7. save metadata.

Do not tune on the test set.

---

## 6. Metric Rules

Delay regression:

- MAE;
- RMSE;
- R².

SLA classification:

- F1;
- Macro F1;
- precision;
- recall;
- confusion matrix.

Carbon regression:

- MAE;
- RMSE;
- R².

YOLO:

- mAP50;
- mAP50-95;
- precision;
- recall.

Maintenance regression:

- MAE;
- RMSE.

Do not use `accuracy` for regression.

---

## 7. Explainability Rules

Explanation text must use actual values.

Good:

```text
Hub dwell time is 82 min, 47 min above its 35 min baseline.
```

Bad:

```text
AI detected operational inefficiency.
```

Route explanations must compare computed metrics.

Good:

```text
Balanced AI reduces SLA risk from 81% to 24% and estimated CO₂ from 4.2 kg to 3.8 kg.
```

---

## 8. Route Optimization Rules

- Normalize objectives before weighting.
- Store objective weights.
- Validate sum of weights.
- Preserve negative improvement.
- Never call Haversine road distance.
- Capacity constraints must be checked.
- Every route must visit required stops exactly once unless the model explicitly supports split delivery.
- GA output must be repaired or rejected if invalid.
- OR-Tools remains a baseline/fallback.

---

## 9. Carbon Rules

All emission factors belong in config.

Every carbon response should include:

- estimate;
- units;
- source;
- assumptions.

Do not call prototype carbon estimates certified emissions.

---

## 10. Decision Engine Rules

The decision engine is policy logic.

It must be:

- deterministic;
- configurable;
- auditable.

Every decision stores evidence.

Do not use a generative AI model as the core decision authority.

---

## 11. Database Rules

- Repositories own SQL.
- Enable foreign keys.
- Use transactions for multi-table writes.
- Store timestamps in ISO-compatible format.
- Store JSON only for flexible structured fields.
- Index frequently filtered IDs and timestamps.
- Do not expose internal integer IDs as primary user-facing entity names.

---

## 12. API Rules

- Use nouns in endpoint paths.
- Use HTTP status codes correctly.
- Return structured errors.
- Do not expose stack traces.
- Validate file types and sizes.
- Use explicit request/response schemas.
- Document endpoints.

---

## 13. Frontend Rules

Pages call `api_client.py`.

Pages do not:

- open database;
- load models;
- run optimization.

Every page must have:

- header;
- one-sentence purpose;
- environment badge;
- loading state;
- error state;
- empty state.

No dead buttons.

---

## 14. Testing Rules

A task is not complete until:

- happy path is tested;
- at least one failure path is tested;
- code is imported successfully.

Critical algorithms require unit tests.

Critical APIs require API tests.

The full demo requires end-to-end verification.

---

## 15. Git Rules

Recommended:

- `main` = stable;
- `develop` = integration;
- feature branches.

Example:

```text
feature/delay-model
feature/route-ga
feature/hub-risk
feature/streamlit-dashboard
```

Commit messages:

```text
feat: add SLA risk classifier
fix: validate GA route coverage
test: add hub congestion edge cases
docs: update carbon assumptions
```

Do not commit:

- `.env`;
- local DB files unless a demo DB is intentionally versioned;
- large model weights without repository policy;
- secrets;
- raw private data.

---

## 16. Definition of Done

A feature is Done when:

- requirement is implemented;
- tests pass;
- error handling exists;
- UI/API labels are honest;
- documentation is updated;
- task checkbox is marked complete only after verification.
