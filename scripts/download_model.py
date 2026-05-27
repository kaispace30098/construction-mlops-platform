import os
import shutil

import mlflow
from mlflow import MlflowClient

MODEL_NAME = "construction-cost-model"
CHAMPION_ALIAS = "champion"
OUTPUT_DIR = "model_artifact"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI")

mlflow.set_tracking_uri(TRACKING_URI)
client = MlflowClient()

try:
    version = client.get_model_version_by_alias(MODEL_NAME, CHAMPION_ALIAS)
except Exception:
    print(f"ERROR: No '{CHAMPION_ALIAS}' alias found. Did evaluate.py register a model?")
    raise SystemExit(1)

model_uri = f"models:/{MODEL_NAME}@{CHAMPION_ALIAS}"
print(f"Downloading {MODEL_NAME} v{version.version} (alias: '{CHAMPION_ALIAS}')...")

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=OUTPUT_DIR)
print(f"Model downloaded to ./{OUTPUT_DIR}/")
