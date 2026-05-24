# NEXT_STEPS.md
# What was built and what comes next
# Last updated: 2026-05-24

---

## What is done (Repo 1: construction-mlops-platform)

- [x] Dataset regenerated with realistic feature-target correlations (R2 = 0.935)
- [x] 70 / 15 / 15 train / val / holdout split in preprocess.py
- [x] train.py logs: data_version hash, trigger tag (local vs ci), holdout metrics, holdout CSV artifact
- [x] Railway MLflow server running at https://caddy-production-1344.up.railway.app
- [x] .env / .env.example / .gitignore set up correctly (.env is gitignored)
- [x] .github/workflows/train-deploy.yml created (Job 1 train is active, Jobs 2 and 3 are commented placeholders)
- [x] README.md written in UTF-8

---

## What comes next (in order)

### Step 1 — src/evaluate.py  (Repo 1)
Champion vs challenger comparison on holdout set.
- Load current Production model from MLflow Registry (champion)
- Load new model from the latest run (challenger)
- Compare RMSE on the holdout set saved as MLflow artifact
- If challenger wins by threshold (e.g. 2%) -> register to MLflow Staging
- If challenger loses -> exit with error code 1 (fails CI, stops pipeline)

### Step 2 — Uncomment Job 2 in train-deploy.yml  (Repo 1)
Wire evaluate.py into CI after train job passes.

### Step 3 — serving/app.py  (Repo 1)
FastAPI wrapper that serves the model as an HTTP API.
- POST /predict  -> accepts JSON feature payload, returns predicted Material_Cost_USD
- GET  /health   -> liveness probe for Kubernetes
- Load model from local path (model is baked into Docker image at build time)

### Step 4 — Dockerfile  (Repo 1)
Package FastAPI app + downloaded model artifact into a single image.
- Base image: python:3.11-slim
- Install: fastapi, uvicorn, xgboost, mlflow-skinny, pandas
- Copy serving/app.py
- Copy model artifact (downloaded from Railway MLflow during CI build)
- CMD: uvicorn serving.app:app --host 0.0.0.0 --port 8080

### Step 5 — scripts/download_model.py  (Repo 1)
Script that CI runs before docker build.
- Connects to Railway MLflow
- Downloads the latest Staging model artifact (model.xgb)
- Saves to local path so Dockerfile can COPY it

### Step 6 — Uncomment Job 3 in train-deploy.yml  (Repo 1)
Full package job:
  1. Run scripts/download_model.py
  2. docker build -t ghcr.io/tomc3/construction-model:{git_sha} .
  3. docker push ghcr.io/tomc3/construction-model:{git_sha}
  4. Commit new image tag to Repo 2 (construction-gitops)

---

## Repo 2 to create: construction-gitops

New separate GitHub repo. ArgoCD watches this repo.
Files needed:
  deployment.yaml   <- references ghcr.io image tag, updated by Repo 1 CI
  service.yaml      <- exposes port 8080 inside kind cluster
  ingress.yaml      <- optional, routes external traffic

### Step 7 — Create Repo 2 and write manifests
deployment.yaml structure:
  image: ghcr.io/tomc3/construction-model:{tag}   <- this line gets auto-updated by CI
  replicas: 1
  resources: limits cpu 500m / memory 512Mi

### Step 8 — Set up kind cluster locally
Install kind if not done:
  winget install Kubernetes.kind
Create cluster:
  kind create cluster --name mlops

### Step 9 — Install ArgoCD in kind
  kubectl create namespace argocd
  kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
  kubectl port-forward svc/argocd-server -n argocd 8080:443

### Step 10 — Connect ArgoCD to Repo 2
Create ArgoCD Application pointing at construction-gitops repo.
ArgoCD will auto-sync whenever Repo 1 CI commits a new image tag to Repo 2.

---

## Environment variables needed

Local (.env file, gitignored):
  MLFLOW_TRACKING_URI      = https://caddy-production-1344.up.railway.app
  MLFLOW_TRACKING_USERNAME = admin
  MLFLOW_TRACKING_PASSWORD = (see Railway dashboard)

GitHub Actions Secrets (already added):
  MLFLOW_TRACKING_URI
  MLFLOW_TRACKING_USERNAME
  MLFLOW_TRACKING_PASSWORD

GitHub Actions Secrets (to add when doing Step 6):
  GITHUB_TOKEN   <- auto-provided by GitHub Actions, no manual setup needed
  GITOPS_TOKEN   <- personal access token to commit to Repo 2 from Repo 1 CI

---

## Architecture reminder

  git push (Repo 1)
      |
  GitHub Actions
      |-- Job 1: train        -> logs to Railway MLflow
      |-- Job 2: evaluate     -> champion vs challenger -> register Staging
      |-- Job 3: package      -> docker build -> ghcr.io -> update Repo 2 tag
                                                                    |
                                                              ArgoCD detects
                                                                    |
                                                            kind cluster deploys
                                                            new model serving pod