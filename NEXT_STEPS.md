# NEXT_STEPS.md
# Last updated: 2026-05-25

## Current Status

- [x] Repo 1: construction-cost-model  (CI complete)
  - train -> evaluate (champion/challenger) -> package -> ghcr.io
  - evaluate.py updated to use MLflow Alias API (non-deprecated)
  - Docker image at ghcr.io/kaispace30098/construction-cost-model:latest

- [x] Repo 2: construction-cost-gitops  (CD complete)
  - kind cluster (mlops) running locally
  - ArgoCD installed and synced
  - Pod: READY 1/1, prediction endpoint working
  - Test: $52,706 (high complexity) vs $16,854 (low complexity) ✅

- [ ] GitOps auto-update wiring  (next session)
- [ ] CM: Continuous Monitoring  (after GitOps wiring)

---

## Railway Deletion Note

Railway (MLflow tracking server) has been deleted to save cost.

### What breaks without Railway
- CI `evaluate` job will fail — no MLflow tracking URI to connect to
- `train` job will fail — nowhere to log runs

### Next time: Spin up Railway MLflow again
1. Go to Railway -> New Project -> Deploy Template -> search "MLflow"
   (PostgreSQL + MinIO + Caddy template)
2. After deploy, get the public Caddy URL (e.g. https://caddy-xxxx.up.railway.app)
3. Update `.env`:
   ```
   MLFLOW_TRACKING_URI=https://caddy-xxxx.up.railway.app
   MLFLOW_TRACKING_USERNAME=admin
   MLFLOW_TRACKING_PASSWORD=<from Railway MLflow env vars>
   ```
4. Update GitHub Secrets in construction-cost-model repo:
   - MLFLOW_TRACKING_URI
   - MLFLOW_TRACKING_USERNAME
   - MLFLOW_TRACKING_PASSWORD
5. Push a whitespace change to README to trigger CI
6. First CI run: evaluate.py finds no 'champion' alias -> registers v1 as champion automatically
7. Subsequent runs: challenger must beat champion RMSE by 2% to promote

### evaluate.py alias API (already fixed)
evaluate.py now uses the current MLflow Alias API:
- `get_model_version_by_alias("champion")` instead of deprecated `get_latest_versions(stages=["Production"])`
- `set_registered_model_alias(...)` instead of deprecated `transition_model_version_stage(...)`
- Champion URI: `models:/construction-cost-model@champion`
- First run auto-registers as champion (no manual MLflow UI step needed)

---

## Remaining Task: GitOps auto-update wiring

### What to do
In `.github/workflows/train-deploy.yml`, uncomment the block at the bottom
of the `package` job that clones Repo 2 and updates the image tag.

### GitHub Secret needed
Add secret `GITOPS_TOKEN`:
- Go to GitHub -> Settings -> Developer Settings -> Personal Access Tokens -> Fine-grained
- Repository access: construction-cost-gitops only
- Permissions: Contents (read + write)
- Copy token -> add as GitHub Secret `GITOPS_TOKEN` in construction-cost-model repo

### End-to-end flow when complete
```
git push (Repo 1)
  -> GitHub Actions CI
     -> train    (logs to Railway MLflow)
     -> evaluate (champion/challenger gating)
     -> package  (Docker image -> ghcr.io)
     -> gitops   (updates image tag in Repo 2)
        -> ArgoCD detects Repo 2 changed
        -> kind cluster deploys new pod automatically
```

---

## CM: Continuous Monitoring (future)

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

---

## Full architecture when complete

  Developer pushes code (Repo 1)
      |
  GitHub Actions CI
      |-- train       -> Railway MLflow
      |-- evaluate    -> champion vs challenger (alias API)
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

---

## Key commands to resume

```powershell
# Load env (when Railway is running)
Get-Content C:\Users\tomc3\mlops\.env | Where-Object { $_ -match '^[^#]' } | ForEach-Object { $k, $v = $_ -split '=', 2; [System.Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), 'Process') }

# Check pod status
kubectl get pods -n mlops

# Restart pod to pull new image
kubectl rollout restart deployment construction-cost-model -n mlops

# Test prediction (ArgoCD on 8080, use 9090 for model)
kubectl port-forward svc/argocd-server -n argocd 8080:443
kubectl port-forward svc/construction-cost-model -n mlops 9090:8080

Invoke-RestMethod -Uri http://localhost:9090/predict -Method Post -ContentType "application/json" -Body '{
  "Task_Duration_Days": 45, "Labor_Required": 15, "Equipment_Units": 8,
  "Start_Constraint": 3, "Risk_Level": "High",
  "Resource_Constraint_Score": 6, "Site_Constraint_Score": 7, "Dependency_Count": 4
}'
# Expected: ~$52,706 (high complexity)

Invoke-RestMethod -Uri http://localhost:9090/predict -Method Post -ContentType "application/json" -Body '{
  "Task_Duration_Days": 5, "Labor_Required": 2, "Equipment_Units": 1,
  "Start_Constraint": 0, "Risk_Level": "Low",
  "Resource_Constraint_Score": 1, "Site_Constraint_Score": 1, "Dependency_Count": 0
}'
# Expected: ~$16,854 (low complexity)
```

## Repos

- Repo 1: https://github.com/kaispace30098/construction-cost-model
- Repo 2: https://github.com/kaispace30098/construction-cost-gitops
- GitHub username: kaispace30098
