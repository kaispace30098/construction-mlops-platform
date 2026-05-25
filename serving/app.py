import glob
import os

import pandas as pd
import xgboost as xgb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

RISK_MAP = {"Low": 0, "Medium": 1, "High": 2}

FEATURES = [
    "Task_Duration_Days",
    "Labor_Required",
    "Equipment_Units",
    "Start_Constraint",
    "Risk_Level",
    "Resource_Constraint_Score",
    "Site_Constraint_Score",
    "Dependency_Count",
]

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model")

app = FastAPI(title="Construction Cost Predictor")

# Load XGBoost Booster directly — bypasses the MLflow sklearn wrapper which has
# a known _estimator_type bug in XGBoost 2.1.x when loading via pyfunc/xgboost flavour.
# XGBRegressor.save_model() writes a pure Booster file (UBJSON/JSON); Booster.load_model()
# reads it back without touching the sklearn layer at all.
_model_files = (
    glob.glob(f"{MODEL_PATH}/**/*.ubj", recursive=True)
    + glob.glob(f"{MODEL_PATH}/**/*.xgb", recursive=True)
    + glob.glob(f"{MODEL_PATH}/**/*.json", recursive=True)
)
if not _model_files:
    raise RuntimeError(f"No XGBoost model file found under {MODEL_PATH}")

booster = xgb.Booster()
booster.load_model(_model_files[0])


class PredictRequest(BaseModel):
    Task_Duration_Days: int
    Labor_Required: int
    Equipment_Units: int
    Start_Constraint: int
    Risk_Level: str          # "Low" | "Medium" | "High"
    Resource_Constraint_Score: int
    Site_Constraint_Score: int
    Dependency_Count: int


class PredictResponse(BaseModel):
    predicted_cost_usd: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if req.Risk_Level not in RISK_MAP:
        raise HTTPException(status_code=422, detail="Risk_Level must be Low, Medium, or High")

    data = req.model_dump()
    data["Risk_Level"] = RISK_MAP[data["Risk_Level"]]

    df = pd.DataFrame([data])[FEATURES]
    dmatrix = xgb.DMatrix(df)
    prediction = float(booster.predict(dmatrix)[0])

    return PredictResponse(predicted_cost_usd=prediction)
