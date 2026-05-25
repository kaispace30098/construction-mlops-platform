# construction-cost-model

An MLOps service for construction cost prediction. Covers experiment tracking, CI/CD automation, champion/challenger model evaluation, containerised serving, and GitOps-based deployment via ArgoCD.

---
<img width="2541" height="1144" alt="image" src="https://github.com/user-attachments/assets/235df238-d83c-43b7-b6af-415781898ddb" />

## Architecture

```
construction-cost-model (this repo)            construction-cost-gitops (Repo 2)
------------------------------------           ----------------------------------
src/train.py      -> train model               deployment.yaml
src/evaluate.py   -> champion vs challenger    service.yaml
src/preprocess.py -> feature engineering       ingress.yaml
Dockerfile        -> package model server            |
.github/workflows -> CI pipeline                     |
       |                                        ArgoCD watches this
       | on git push                                  |
       v                                             v
  GitHub Actions                             kind cluster (local)
  train -> evaluate -> register -> build       model serving pod
       |
       v
  Railway MLflow
  (experiment tracking + model registry)
```

---

## Data

Synthetic construction project dataset (1,300 rows).

| Feature | Description |
|---------|-------------|
| `Task_Duration_Days` | Duration of the construction task |
| `Labor_Required` | Number of workers required |
| `Equipment_Units` | Number of equipment units |
| `Start_Constraint` | Scheduling constraint score |
| `Risk_Level` | Low / Medium / High |
| `Resource_Constraint_Score` | Resource availability score |
| `Site_Constraint_Score` | Site difficulty score |
| `Dependency_Count` | Number of task dependencies |

**Target:** `Material_Cost_USD`

**Split:** 70% train / 15% val / 15% holdout

---

## Model

XGBoost regressor trained with the following parameters:

```python
n_estimators     = 300
max_depth        = 6
learning_rate    = 0.05
subsample        = 0.8
colsample_bytree = 0.8
```

**Holdout metrics:**

| Metric | Value |
|--------|-------|
| R2     | 0.935 |
| RMSE   | 4,031 |
| MAE    | 3,202 |

---

## MLflow Tracking

All experiments are logged to a central MLflow server hosted on Railway.

Every run records:

- `data_version` - MD5 hash of the training CSV
- `trigger` - `local` (developer run) or `ci` (GitHub Actions run)
- Parameters, metrics, holdout dataset artifact, and model artifact

---

## CI/CD Pipeline

| Job | Trigger | What it does |
|-----|---------|--------------|
| `train` | git push to main | Train model, log run to MLflow |
| `evaluate` | after train | Compare vs Production champion on holdout set |
| `package` | after evaluate passes | Build Docker image, push to ghcr.io |

---

## Railway MLflow Setup

Railway hosts the MLflow tracking server (PostgreSQL + MinIO + Caddy).
**When you delete and recreate Railway, do these 4 things:**

### 1. Update .env (local)

Open `.env` and replace with new values from Railway dashboard:

```
MLFLOW_TRACKING_URI=https://your-new-caddy-url.up.railway.app
MLFLOW_TRACKING_USERNAME=admin
MLFLOW_TRACKING_PASSWORD=your_new_password
```

### 2. Reload .env in your terminal (PowerShell)

```powershell
Get-Content .env | Where-Object { $_ -match '^[^#]' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process')
}
```

### 3. Update GitHub Secrets

```
github.com/kaispace30098/construction-cost-model
-> Settings -> Secrets and variables -> Actions
-> Update: MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME, MLFLOW_TRACKING_PASSWORD
```

### 4. Trigger CI to populate new Railway MLflow

Add a space anywhere in this README and push -- this triggers all 3 CI jobs,
trains the model and registers it to Staging in the new Railway instance.

```powershell
# add a space to README, then:
git add README.md
git commit -m "trigger CI for new Railway instance"
git push origin main
```

---

## Starting Repo 2 (construction-cost-gitops)

**Before starting ArgoCD / kind setup, do this first in Railway MLflow UI:**

```
Railway MLflow UI -> Models -> construction-cost-model
-> find the latest Staging version
-> click Stage -> transition to Production
```

This is required because evaluate.py compares new models against the Production
champion. Without a Production model, every push registers to Staging (no gating).
Once one version is Production, the 2% improvement threshold kicks in properly.

**Then proceed with Repo 2:**
- Create repo: construction-cost-gitops
- Write deployment.yaml, service.yaml (pull image from ghcr.io/kaispace30098/construction-cost-model:latest)
- Install ArgoCD in kind cluster
- Connect ArgoCD to construction-cost-gitops
- Uncomment the GitOps update block at the bottom of .github/workflows/train-deploy.yml
  (search for GITOPS_TOKEN -- that block updates Repo 2 image tag automatically)
- Add GITOPS_TOKEN to GitHub Secrets (personal access token with repo write access)

---

## Local Development

Requirements: Python 3.11+

```powershell
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME, MLFLOW_TRACKING_PASSWORD

# Load .env (PowerShell)
Get-Content .env | Where-Object { $_ -match '^[^#]' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process')
}

# Train locally
python src/train.py
```

---

## Repository Structure

```
construction-cost-model/
|-- .github/
|   \-- workflows/
|       \-- train-deploy.yml       # CI/CD pipeline (3 jobs)
|-- data/
|   \-- construction_dataset.csv
|-- scripts/
|   \-- download_model.py          # downloads Staging model for Docker build
|-- serving/
|   \-- app.py                     # FastAPI wrapper POST /predict GET /health
|-- src/
|   |-- preprocess.py              # Feature engineering and 70/15/15 split
|   |-- train.py                   # Training, logging, holdout evaluation
|   \-- evaluate.py                # Champion vs challenger
|-- .env.example                   # Environment variable template
|-- .gitignore
|-- Dockerfile                     # Packages FastAPI app + model artifact
|-- requirements.txt               # Training dependencies
|-- requirements-serve.txt         # Serving dependencies
\-- README.md
```