import os
import sys

import mlflow
import mlflow.xgboost
import numpy as np
from mlflow import MlflowClient
from sklearn.metrics import mean_squared_error

from preprocess import load_and_split

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(_ROOT, "data", "construction_dataset.csv")
MODEL_NAME = "construction-cost-model"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", f"file:///{_ROOT}/mlruns")
EXPERIMENT_NAME = "construction-cost-prediction"
IMPROVEMENT_THRESHOLD = 0.02  # challenger must beat champion by at least 2%


def compute_rmse(model, X, y):
    y_pred = model.predict(X)
    return float(np.sqrt(mean_squared_error(y, y_pred)))


def get_latest_ci_run(client):
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        print("ERROR: Experiment not found")
        sys.exit(1)

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="tags.trigger = 'ci'",
        order_by=["start_time DESC"],
        max_results=1,
    )
    if not runs:
        print("ERROR: No CI runs found. Did train job complete successfully?")
        sys.exit(1)

    return runs[0]


def get_champion(client):
    try:
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if versions:
            return versions[0]
    except Exception:
        pass
    return None


def register_as_staging(client, challenger_uri):
    mv = mlflow.register_model(challenger_uri, MODEL_NAME)
    client.transition_model_version_stage(MODEL_NAME, mv.version, "Staging")
    print(f"Registered {MODEL_NAME} v{mv.version} -> Staging")


def main():
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient()

    # Holdout set — same random_state as train.py so same rows every time
    _, _, X_holdout, _, _, y_holdout = load_and_split(DATA_PATH)

    # Challenger: latest CI run
    latest_run = get_latest_ci_run(client)
    challenger_uri = f"runs:/{latest_run.info.run_id}/model"
    print(f"Challenger run ID : {latest_run.info.run_id}")

    challenger_model = mlflow.xgboost.load_model(challenger_uri)
    challenger_rmse = compute_rmse(challenger_model, X_holdout, y_holdout)
    print(f"Challenger RMSE   : {challenger_rmse:.2f}")

    # Champion: current Production model
    champion_version = get_champion(client)

    if champion_version is None:
        print("No Production champion found. First deployment — registering to Staging.")
        register_as_staging(client, challenger_uri)
        sys.exit(0)

    # Compare challenger vs champion on same holdout
    champion_uri = f"models:/{MODEL_NAME}/Production"
    champion_model = mlflow.xgboost.load_model(champion_uri)
    champion_rmse = compute_rmse(champion_model, X_holdout, y_holdout)

    improvement = (champion_rmse - challenger_rmse) / champion_rmse
    print(f"Champion RMSE     : {champion_rmse:.2f}")
    print(f"Improvement       : {improvement:.2%}  (required: {IMPROVEMENT_THRESHOLD:.2%})")

    if improvement >= IMPROVEMENT_THRESHOLD:
        print("Challenger wins. Registering to Staging.")
        register_as_staging(client, challenger_uri)
    else:
        print("Challenger did not improve enough. Stopping CI.")
        sys.exit(1)


if __name__ == "__main__":
    main()