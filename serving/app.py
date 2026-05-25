import os

import mlflow.pyfunc
import pandas as pd
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

# Load model once at startup
model = mlflow.pyfunc.load_model(MODEL_PATH)


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
    prediction = float(model.predict(df)[0])

    return PredictResponse(predicted_cost_usd=prediction)