import hashlib
import os
import tempfile

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
from mlflow.models.signature import infer_signature
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from preprocess import FEATURES, TARGET, load_and_split

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(_ROOT, "data", "construction_dataset.csv")
MODEL_NAME = "construction-cost-model"

TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", f"file:///{_ROOT}/mlruns")

PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}


def train():
    X_train, X_val, X_holdout, y_train, y_val, y_holdout = load_and_split(DATA_PATH)

    # data version: MD5 hash of the CSV (first 8 chars)
    data_hash = hashlib.md5(open(DATA_PATH, "rb").read()).hexdigest()[:8]

    print(f"Split sizes — train: {len(X_train)}, val: {len(X_val)}, holdout: {len(X_holdout)}")

    with mlflow.start_run():
        # ── params ────────────────────────────────────────────────────────
        mlflow.set_tag("trigger", "ci" if os.environ.get("CI") else "local")
        mlflow.log_param("data_version", data_hash)
        mlflow.log_params(PARAMS)

        # ── training (val set for XGBoost early-stop monitoring) ──────────
        model = XGBRegressor(**PARAMS)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        # ── metrics on holdout (unbiased, never seen during training) ─────
        y_pred = model.predict(X_holdout)
        rmse = float(np.sqrt(mean_squared_error(y_holdout, y_pred)))
        mae  = float(mean_absolute_error(y_holdout, y_pred))
        r2   = float(r2_score(y_holdout, y_pred))

        mlflow.log_metrics({"rmse": rmse, "mae": mae, "r2": r2})
        print(f"Holdout — RMSE: {rmse:.2f}  MAE: {mae:.2f}  R2: {r2:.4f}")

        # ── log holdout set as artifact (for evaluate.py later) ──────────
        with tempfile.TemporaryDirectory() as tmpdir:
            holdout_path = os.path.join(tmpdir, "holdout.csv")
            holdout_df = X_holdout.copy()
            holdout_df[TARGET] = y_holdout.values
            holdout_df.to_csv(holdout_path, index=False)
            mlflow.log_artifact(holdout_path, artifact_path="data")

        # ── log model ─────────────────────────────────────────────────────
        signature  = infer_signature(X_train, model.predict(X_train))
        model_info = mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            signature=signature,
            input_example=X_train.iloc[:3],
        )

        print(f"Model logged : {model_info.model_uri}")
        print(f"Run ID       : {mlflow.active_run().info.run_id}")
        print(f"Data version : {data_hash}")


if __name__ == "__main__":
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment("construction-cost-prediction")
    train()
