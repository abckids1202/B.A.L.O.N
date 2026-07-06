from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from database.connection import initialize_database
from database import repositories as repo

FEATURES = ["traffic_index","weather_severity","hub_dwell_excess","sla_buffer_minutes","route_distance_km","load_weight_kg","loading_compliance_score"]

def dataset(n=420, seed=42):
    rng = np.random.default_rng(seed)
    X = np.column_stack([
        rng.uniform(.1,.95,n), rng.uniform(0,.9,n), rng.uniform(0,70,n),
        rng.uniform(-50,180,n), rng.uniform(8,45,n), rng.uniform(20,750,n), rng.uniform(55,98,n)
    ])
    delay = X[:,0]*42 + X[:,1]*28 + X[:,2]*.65 + np.maximum(-X[:,3],0)*.3 + (90-X[:,6])*.25 + rng.normal(0,5,n)
    delay = np.maximum(delay, 0)
    prob = np.clip(delay/85 + X[:,0]*.18 + X[:,1]*.12 + X[:,2]/250 - X[:,3]/260, 0, 1)
    breach = (prob >= .5).astype(int)
    carbon = X[:,4] / 11 * 2.68 * (1 + .18*np.minimum(X[:,5]/900,1.5)) + X[:,0]*.4 + rng.normal(0,.12,n)
    return X, delay, breach, carbon

def register(name, version, model_type, path, rows, metrics):
    repo.execute("INSERT OR REPLACE INTO model_registry(name,version,model_type,file_path,dataset_type,training_rows,feature_names_json,metrics_json,availability,fallback_state,training_timestamp) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (name, version, model_type, str(path), "synthetic prototype target", rows, json.dumps(FEATURES), json.dumps(metrics), "AVAILABLE", "Rule fallback available", datetime.now(timezone.utc).isoformat()))

def train_delay():
    initialize_database()
    X, y, _, _ = dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)
    model = HistGradientBoostingRegressor(random_state=42).fit(X_train, y_train)
    pred = model.predict(X_test)
    metrics = {"MAE": round(float(mean_absolute_error(y_test,pred)),3), "RMSE": round(float(mean_squared_error(y_test,pred) ** 0.5),3), "R2": round(float(r2_score(y_test,pred)),3), "disclosure":"Synthetic target logic only."}
    path = Path("models/delay_model.joblib"); path.parent.mkdir(exist_ok=True); joblib.dump({"model": model, "features": FEATURES}, path)
    register("delay_model","v1","HistGradientBoostingRegressor",path,len(X),metrics); print(metrics)

def train_sla():
    initialize_database()
    X, _, y, _ = dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42, stratify=y)
    model = RandomForestClassifier(n_estimators=90, random_state=42).fit(X_train, y_train)
    pred = model.predict(X_test)
    metrics = {"F1": round(float(f1_score(y_test,pred)),3), "Macro F1": round(float(f1_score(y_test,pred,average='macro')),3), "precision": round(float(precision_score(y_test,pred)),3), "recall": round(float(recall_score(y_test,pred)),3), "disclosure":"Synthetic target logic only."}
    path = Path("models/sla_model.joblib"); path.parent.mkdir(exist_ok=True); joblib.dump({"model": model, "features": FEATURES}, path)
    register("sla_model","v1","RandomForestClassifier",path,len(X),metrics); print(metrics)

def train_carbon():
    initialize_database()
    X, _, _, y = dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)
    model = RandomForestRegressor(n_estimators=90, random_state=42).fit(X_train, y_train)
    pred = model.predict(X_test)
    metrics = {"MAE": round(float(mean_absolute_error(y_test,pred)),3), "RMSE": round(float(mean_squared_error(y_test,pred) ** 0.5),3), "R2": round(float(r2_score(y_test,pred)),3), "disclosure":"Synthetic formula target only; deterministic baseline remains authoritative."}
    path = Path("models/carbon_model.joblib"); path.parent.mkdir(exist_ok=True); joblib.dump({"model": model, "features": FEATURES}, path)
    register("carbon_model","v1","RandomForestRegressor",path,len(X),metrics); print(metrics)

def train_maintenance():
    initialize_database()
    register("maintenance_rules","v1","Deterministic rule engine","modules/maintenance/rules.py",0,{"source":"rules","disclosure":"No mechanical failure certainty."}); print("registered maintenance rules")

def register_yolo_demo():
    initialize_database()
    register("loading_yolo","demo-v1","Deterministic Demo Detection Mode","models/loading_yolo.pt",0,{"metrics_available":False,"disclosure":"No YOLO weights provided; demo mode is synthetic."}); print("registered yolo demo mode")
