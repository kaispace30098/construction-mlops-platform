# NEXT_STEPS.md
# Last updated: 2026-05-24
## Repo 1 (construction-cost-model) CI pipeline is COMPLETE.

---

## Status

- [x] Repo 1: construction-cost-model  (CI complete)
  - train -> evaluate (champion/challenger) -> package -> ghcr.io
  - Railway MLflow (PostgreSQL + MinIO + Caddy)
  - Docker image at ghcr.io/kaispace30098/construction-cost-model:latest

- [ ] Repo 2: construction-cost-gitops  (CD - next session)
- [ ] CM: Continuous Monitoring         (after Repo 2)

---

## Repo 2: construction-cost-gitops (CD)

### Before starting - do this first
1. Recreate Railway MLflow (PostgreSQL + MinIO + Caddy template)
2. Update .env and GitHub Secrets (see README Railway Setup section)
3. Push a space change to README to trigger CI and populate new Railway
4. Go to Railway MLflow UI -> Models -> construction-cost-model
   -> promote latest Staging version to Production
   (required so evaluate.py champion comparison works correctly)

### Step 1 - Create Repo 2 on GitHub
New repo: construction-cost-gitops (public)

### Step 2 - Write Kubernetes manifests

deployment.yaml
  - image: ghcr.io/kaispace30098/construction-cost-model:latest
  - replicas: 1
  - port: 8080
  - resources: limits cpu 500m / memory 512Mi
  - livenessProbe: GET /health

service.yaml
  - type: ClusterIP
  - port: 8080

kustomization.yaml
  - references deployment.yaml and service.yaml

### Step 3 - Set up kind cluster locally
  kind create cluster --name mlops

### Step 4 - Install ArgoCD in kind
  kubectl create namespace argocd
  kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
  kubectl port-forward svc/argocd-server -n argocd 8080:443

### Step 5 - Connect ArgoCD to Repo 2
  Create ArgoCD Application pointing at construction-cost-gitops
  ArgoCD will auto-sync when image tag changes in Repo 2

### Step 6 - Uncomment GitOps update block in Repo 1 CI
  In .github/workflows/train-deploy.yml, uncomment the bottom block in Job 3
  that clones Repo 2 and updates the image tag.
  Add GitHub Secret: GITOPS_TOKEN (personal access token, repo write scope)

### Step 7 - End to end test
  git push Repo 1
  -> CI: train -> evaluate -> package -> update Repo 2 image tag
  -> ArgoCD detects Repo 2 changed
  -> kind cluster deploys new model serving pod
  -> curl http://localhost:8080/predict with test payload
  -> verify prediction returns Material_Cost_USD

---

## CM: Continuous Monitoring (after Repo 2)

CM watches the deployed model and triggers retraining when it degrades.
No 3rd repo needed -- split between Repo 1 and Repo 2.

### What goes in Repo 1 (construction-cost-model)

serving/app.py
  - add /metrics endpoint (Prometheus format)
  - log prediction input distribution, response time, prediction values

src/monitor.py
  - compares live prediction distribution vs training distribution
  - detects data drift (feature distribution shift)
  - detects model degradation (prediction distribution shift)
  - exits 1 if drift exceeds threshold -> triggers retraining

.github/workflows/monitor.yml (new file)
  - scheduled cron: runs every day at 6am
  - runs python src/monitor.py
  - if drift detected -> triggers train-deploy.yml automatically

### What goes in Repo 2 (construction-cost-gitops)

monitoring/
  prometheus-config.yaml   <- scrapes /metrics from serving pod
  grafana-dashboard.yaml   <- visualises online metrics and drift

### Metrics to monitor

| Metric | What it catches |
|--------|----------------|
| Prediction mean / std | model output distribution shift |
| Feature distributions | data drift (input changed) |
| Request latency | serving performance |
| Error rate | serving failures |
| RMSE vs holdout baseline | model degradation |

### Scheduler cron in Repo 1

  on:
    schedule:
      - cron: 0 6 * * *   # daily at 6am
  jobs:
    monitor:
      steps:
        - run: python src/monitor.py
          # drift > threshold -> auto trigger retraining pipeline

---

## Full architecture when complete

  Developer pushes code (Repo 1)
      |
  GitHub Actions CI
      |-- train       -> Railway MLflow
      |-- evaluate    -> champion vs challenger -> Staging
      |-- package     -> Docker image -> ghcr.io
      |-- gitops      -> update image tag in Repo 2
                                |
                          ArgoCD detects
                                |
                      kind cluster deploys new pod
                                |
                      Prometheus scrapes /metrics
                                |
                      Grafana shows online metrics
                                |
                      monitor.yml cron (daily)
                                |
                      drift detected? -> trigger retraining
                                |
                      back to top (self-healing loop)