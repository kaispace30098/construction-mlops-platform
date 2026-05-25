import os
import shutil

import mlflow
from mlflow import MlflowClient

MODEL_NAME = "construction-cost-model"
OUTPUT_DIR = "model_artifact"
TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI")

mlflow.set_tracking_uri(TRACKING_URI)
client = MlflowClient()

versions = client.get_latest_versions(MODEL_NAME, stages=["Staging"])
if not versions:
    print("ERROR: No Staging model found. Did evaluate.py register a model?")
    raise SystemExit(1)

version = versions[0]
model_uri = f"models:/{MODEL_NAME}/Staging"
print(f"Downloading {MODEL_NAME} v{version.version} from Staging...")

if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

mlflow.artifacts.download_artifacts(artifact_uri=model_uri, dst_path=OUTPUT_DIR)
print(f"Model downloaded to ./{OUTPUT_DIR}/")