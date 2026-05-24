# construction-cost-model

An MLOps service for construction cost prediction. Covers experiment tracking, CI/CD automation, champion/challenger model evaluation, containerised serving, and GitOps-based deployment via ArgoCD.

---

## Architecture

```
construction-mlops-platform (this repo)        construction-gitops (Repo 2)
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€         â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
| `package` | after evaluate passes | Build Docker image, push to ghcr.io, update Repo 2 |

---

## Local Development

Requirements: Python 3.11+

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in MLFLOW_TRACKING_URI, MLFLOW_TRACKING_USERNAME, MLFLOW_TRACKING_PASSWORD

# Train locally
python src/train.py
```

---

## Repository Structure

```
construction-mlops-platform/
â”œâ”€â”€ .github/
â”‚   â””â”€â”€ workflows/
â”‚       â””â”€â”€ train-deploy.yml   # CI/CD pipeline
â”œâ”€â”€ data/
â”‚   â””â”€â”€ construction_dataset.csv
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ preprocess.py          # Feature engineering and 70/15/15 split
â”‚   â”œâ”€â”€ train.py               # Training, logging, holdout evaluation
â”‚   â””â”€â”€ evaluate.py            # Champion vs challenger (coming next)
â”œâ”€â”€ .env.example               # Environment variable template
â”œâ”€â”€ .gitignore
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md
```